"""
执行层: 状态机驱动的 DSL 执行器
支持: 暂停/恢复/停止, 循环, 条件, 子流程, 事件回调
      子程序(CALL/SUBROUTINE), IMPORT, RETURN, 变量插值
"""

from __future__ import annotations
import os
import re
import time
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from typing import Callable, Dict, Optional, Any
from dataclasses import dataclass, field

from engine.dsl_parser import ASTNode, NodeType, DSLParser


class ExecutorState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    FINISHED = "finished"


@dataclass
class ExecutionContext:
    variables: Dict[str, Any] = field(default_factory=dict)
    loop_count: Dict[str, int] = field(default_factory=dict)
    max_loops: int = 9999
    retry_limit: int = 3
    timeout: float = 30.0
    max_call_depth: int = 50


class ExecutionError(Exception):
    pass


class ReturnSignal(Exception):
    """从子程序返回的信号，携带返回值"""
    def __init__(self, value: Any = None):
        self.value = value
        super().__init__()


class DSLExecutor:
    """
    状态机执行器
    事件系统: on_node_start, on_node_done, on_error, on_state_change
    """

    def __init__(self, action_handler=None):
        self._state = ExecutorState.IDLE
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._stop_flag = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._action_handler = action_handler
        self._ctx: Optional[ExecutionContext] = None  # 当前执行上下文引用

        # 层次化 DSL 支持
        self._subroutines: dict[str, ASTNode] = {}
        self._scope_stack: list[dict[str, Any]] = [{}]  # 作用域链
        self._call_depth = 0

        # 线程安全
        self._action_lock = threading.Lock()

        # 异质执行：handler 注册表
        self._handlers: dict[str, Any] = {"default": self._action_handler}

        # 事件回调
        self._callbacks: Dict[str, list[Callable]] = {
            "node_start": [],
            "node_done": [],
            "error": [],
            "state_change": [],
            "log": [],
        }

    # ── 作用域管理 ────────────────────────────────────────────────
    def _current_scope(self) -> dict:
        return self._scope_stack[-1]

    def _push_scope(self, bindings: Optional[dict] = None):
        self._scope_stack.append(bindings or {})

    def _pop_scope(self) -> dict:
        return self._scope_stack.pop()

    def _resolve_var(self, name: str) -> Optional[Any]:
        for scope in reversed(self._scope_stack):
            if name in scope:
                return scope[name]
        return None

    def _set_var(self, name: str, value: Any):
        """设置变量（在当前作用域），同步到 ctx.variables 供 ActionHandler 访问"""
        self._current_scope()[name] = value
        if self._ctx is not None:
            self._ctx.variables[name] = value

    def _interpolate(self, text: str) -> str:
        """替换 {var} 为变量值"""
        def replacer(m):
            var_name = m.group(1)
            val = self._resolve_var(var_name)
            if val is not None:
                return str(val)
            return m.group(0)  # 保留未解析的占位符
        return re.sub(r"\{(\w+)\}", replacer, text)

    # ── 公开控制 API ─────────────────────────────────────────────
    def run_dsl(self, source: str, ctx: Optional[ExecutionContext] = None):
        """解析并异步执行 DSL"""
        if self._state == ExecutorState.RUNNING:
            raise ExecutionError("执行器已在运行中")
        if self._state in (ExecutorState.ERROR, ExecutorState.FINISHED):
            self._reset_state_no_run()
        try:
            parser = DSLParser()
            ast = parser.parse(source)
        except Exception as e:
            return {"success": False, "error": str(e)}
        self._subroutines = parser.subroutines
        ctx = ctx or ExecutionContext()
        self._reset_state(ctx)
        self._thread = threading.Thread(
            target=self._run_thread, args=(ast, ctx), daemon=True
        )
        self._thread.start()
        return {"success": True, "state": self._state.value, "thread": True}

    def run_dsl_sync(self, source: str, ctx: Optional[ExecutionContext] = None):
        """同步执行 DSL（阻塞），返回结果 dict"""
        if self._state in (ExecutorState.ERROR, ExecutorState.FINISHED):
            self._reset_state_no_run()
        try:
            parser = DSLParser()
            ast = parser.parse(source)
        except Exception as e:
            return {"success": False, "error": f"DSL 解析失败: {e}"}
        self._subroutines = parser.subroutines
        ctx = ctx or ExecutionContext()
        self._reset_state(ctx)
        try:
            self._execute_node(ast, ctx)
            if not self._stop_flag.is_set():
                self._set_state(ExecutorState.FINISHED)
            return {"success": True, "state": self._state.value}
        except Exception as e:
            self._set_state(ExecutorState.ERROR)
            return {"success": False, "error": str(e)}

    def _reset_state(self, ctx: ExecutionContext):
        self._stop_flag.clear()
        self._pause_event.set()
        self._scope_stack = [dict(ctx.variables)]
        self._call_depth = 0
        self._ctx = ctx
        self._set_state(ExecutorState.RUNNING)

    def _reset_state_no_run(self):
        """从 ERROR/FINISHED 重置回 IDLE，不清除 scope"""
        self._stop_flag.clear()
        self._pause_event.set()
        self._set_state(ExecutorState.IDLE)

    def reset(self):
        """公开 API：将执行器重置为 IDLE 状态，清除作用域"""
        self._stop_flag.clear()
        self._pause_event.set()
        self._scope_stack = [{}]
        self._call_depth = 0
        self._set_state(ExecutorState.IDLE)

    def pause(self):
        if self._state == ExecutorState.RUNNING:
            self._pause_event.clear()
            self._set_state(ExecutorState.PAUSED)
        return self._state.value

    def resume(self):
        if self._state == ExecutorState.PAUSED:
            self._pause_event.set()
            self._set_state(ExecutorState.RUNNING)
        return self._state.value

    def stop(self):
        self._stop_flag.set()
        self._pause_event.set()
        self._set_state(ExecutorState.STOPPED)
        return self._state.value

    @property
    def state(self) -> ExecutorState:
        return self._state

    # ── 事件注册 ─────────────────────────────────────────────────
    def on(self, event: str, callback: Callable):
        self._callbacks[event].append(callback)

    def register_handler(self, name: str, handler: Callable):
        """注册异质执行 handler，可在 WITH <name> 中使用"""
        self._handlers[name] = handler

    def _emit(self, event: str, **kwargs):
        for cb in self._callbacks.get(event, []):
            try:
                cb(**kwargs)
            except Exception as e:
                self._log(f"  [emit] {event} callback error: {e}")

    # ── 内部执行 ─────────────────────────────────────────────────
    def _run_thread(self, ast: ASTNode, ctx: ExecutionContext):
        try:
            self._execute_node(ast, ctx)
            if not self._stop_flag.is_set():
                self._set_state(ExecutorState.FINISHED)
        except ReturnSignal:
            # 顶层 RETURN 忽略
            if not self._stop_flag.is_set():
                self._set_state(ExecutorState.FINISHED)
        except Exception as e:
            self._emit("error", message=str(e), traceback=traceback.format_exc())
            self._set_state(ExecutorState.ERROR)

    def _check_control(self):
        self._pause_event.wait()
        if self._stop_flag.is_set():
            raise ExecutionError("执行已被用户停止")

    def _execute_node(self, node: ASTNode, ctx: ExecutionContext):
        self._check_control()

        if node.type == NodeType.SEQUENCE:
            for child in node.children:
                self._execute_node(child, ctx)

        elif node.type == NodeType.CLICK:
            self._exec_click(node, ctx)

        elif node.type == NodeType.TYPE:
            self._exec_type(node, ctx)

        elif node.type == NodeType.LAUNCH:
            self._exec_launch(node, ctx)

        elif node.type == NodeType.WAIT:
            self._exec_wait(node, ctx)

        elif node.type == NodeType.LOOP:
            self._exec_loop(node, ctx)

        elif node.type == NodeType.IF:
            self._exec_if(node, ctx)

        elif node.type == NodeType.RUN:
            self._exec_run(node, ctx)

        elif node.type == NodeType.CALL:
            self._exec_call(node, ctx)

        elif node.type == NodeType.IMPORT:
            self._exec_import(node, ctx)

        elif node.type == NodeType.BREAK:
            raise BreakLoop()

        elif node.type == NodeType.RETURN:
            raise ReturnSignal(node.args)

        elif node.type == NodeType.WHEN:
            self._exec_when(node, ctx)

        elif node.type == NodeType.PARALLEL:
            self._exec_parallel(node, ctx)

        elif node.type == NodeType.WITH:
            self._exec_with(node, ctx)

        elif node.type == NodeType.SCREENSHOT:
            self._exec_screenshot(node, ctx)

        elif node.type == NodeType.WAITSCREEN:
            self._exec_waitscreen(node, ctx)

        elif node.type == NodeType.SCREENSTABLE:
            self._exec_screenstable(node, ctx)

        elif node.type == NodeType.HOTKEY:
            self._exec_hotkey(node, ctx)

        elif node.type == NodeType.FOCUS:
            self._exec_focus(node, ctx)

        elif node.type == NodeType.SET:
            self._exec_set(node, ctx)

        elif node.type == NodeType.OCR_FIND:
            self._exec_ocr_find(node, ctx)

        elif node.type == NodeType.OCR_EXTRACT:
            self._exec_ocr_extract(node, ctx)

        elif node.type == NodeType.REGION_SELECT:
            self._exec_region_select(node, ctx)

        elif node.type == NodeType.IMAGE_FIND:
            self._exec_image_find(node, ctx)

        # SUBROUTINE 定义直接跳过（已在 parser 注册）

    # ── 指令执行 ─────────────────────────────────────────────────
    def _exec_click(self, node: ASTNode, ctx: ExecutionContext):
        raw = node.args
        button = "left"
        if raw.upper().endswith(" RIGHT"):
            button = "right"
            raw = raw[:-6]
        elif raw.upper().endswith(" R"):
            button = "right"
            raw = raw[:-2]
        target = self._interpolate(raw)
        self._emit("node_start", node_type="CLICK", args=target, line=node.line)
        self._log(f"CLICK ({button}): {target}")
        self._call_action("click", target=target, button=button, ctx=ctx)
        self._emit("node_done", node_type="CLICK", args=target, line=node.line)

    def _exec_type(self, node: ASTNode, ctx: ExecutionContext):
        text = self._interpolate(node.args)
        self._emit("node_start", node_type="TYPE", args=text, line=node.line)
        self._log(f"TYPE: {text}")
        self._call_action("type", text=text, ctx=ctx)
        self._emit("node_done", node_type="TYPE", args=text, line=node.line)

    def _exec_launch(self, node: ASTNode, ctx: ExecutionContext):
        target = self._interpolate(node.args)
        self._emit("node_start", node_type="LAUNCH", args=target, line=node.line)
        self._log(f"LAUNCH: {target}")
        self._call_action("launch", target=target, ctx=ctx)
        self._emit("node_done", node_type="LAUNCH", args=target, line=node.line)

    def _exec_wait(self, node: ASTNode, ctx: ExecutionContext):
        condition = self._interpolate(node.args)
        self._emit("node_start", node_type="WAIT", args=condition, line=node.line)
        self._log(f"WAIT: {condition}")
        # 数字条件 => 实际 sleep（无论有无 handler）
        try:
            seconds = float(condition)
            time.sleep(seconds)
            self._emit("node_done", node_type="WAIT", args=condition, line=node.line)
            return
        except ValueError:
            pass
        self._call_action("wait", condition=condition, timeout=ctx.timeout, ctx=ctx)
        self._emit("node_done", node_type="WAIT", args=condition, line=node.line)

    def _exec_loop(self, node: ASTNode, ctx: ExecutionContext):
        raw = node.args or ""
        tag = raw
        # 如果 LOOP 参数是纯数字，当作循环次数；否则当作标签名
        try:
            max_iter = int(raw)
            tag = f"_loop_{raw}"
        except ValueError:
            max_iter = ctx.max_loops
        ctx.loop_count[tag] = 0
        self._emit("node_start", node_type="LOOP", args=node.args, line=node.line)
        self._log(f"LOOP 开始: {raw} ({max_iter}次)")

        while ctx.loop_count[tag] < max_iter:
            self._check_control()
            ctx.loop_count[tag] += 1
            self._log(f"  LOOP [{raw}] 第 {ctx.loop_count[tag]} 次")
            try:
                for child in node.children:
                    self._execute_node(child, ctx)
            except BreakLoop:
                break

        self._emit("node_done", node_type="LOOP", args=node.args, line=node.line)

    def _exec_if(self, node: ASTNode, ctx: ExecutionContext):
        condition = self._interpolate(node.args)
        self._emit("node_start", node_type="IF", args=condition, line=node.line)
        self._log(f"IF: {condition}")
        result = self._call_action("check_condition", condition=condition, ctx=ctx)
        branch = node.children if result else node.else_children
        for child in branch:
            self._execute_node(child, ctx)
        self._emit("node_done", node_type="IF", args=condition, line=node.line)

    def _exec_run(self, node: ASTNode, ctx: ExecutionContext):
        macro = self._interpolate(node.args)
        self._emit("node_start", node_type="RUN", args=macro, line=node.line)
        self._log(f"RUN 宏: {macro}")
        self._call_action("run_macro", macro_name=macro, ctx=ctx)
        self._emit("node_done", node_type="RUN", args=macro, line=node.line)

    def _exec_screenshot(self, node: ASTNode, ctx: ExecutionContext):
        dest = self._interpolate(node.args) if node.args else ""
        self._emit("node_start", node_type="SCREENSHOT", args=dest, line=node.line)
        self._log(f"SCREENSHOT: {dest or '(default)'}")
        result = self._call_action("screenshot", dest=dest, ctx=ctx)
        self._set_var("_screenshot", result)
        self._emit("node_done", node_type="SCREENSHOT", args=dest, line=node.line)

    def _exec_waitscreen(self, node: ASTNode, ctx: ExecutionContext):
        args = self._interpolate(node.args)
        # 语法: WAITSCREEN timeout(秒) 或 WAITSCREEN
        timeout = float(args) if args else 30.0
        self._emit("node_start", node_type="WAITSCREEN", args=str(timeout), line=node.line)
        self._log(f"WAITSCREEN: 等待屏幕变化 (超时{timeout}s)")
        result = self._call_action("wait_screen_change", timeout=timeout, ctx=ctx)
        self._set_var("_screen_changed", result)
        self._emit("node_done", node_type="WAITSCREEN", args=str(timeout), line=node.line)

    def _exec_screenstable(self, node: ASTNode, ctx: ExecutionContext):
        args = self._interpolate(node.args)
        timeout = float(args) if args else 30.0
        self._emit("node_start", node_type="SCREENSTABLE", args=str(timeout), line=node.line)
        self._log(f"SCREENSTABLE: 等待屏幕静止 (超时{timeout}s)")
        result = self._call_action("wait_screen_stable", timeout=timeout, ctx=ctx)
        self._set_var("_screen_stable", result)
        self._emit("node_done", node_type="SCREENSTABLE", args=str(timeout), line=node.line)

    def _exec_hotkey(self, node: ASTNode, ctx: ExecutionContext):
        keys = [k.strip() for k in node.args.split(",")]
        self._emit("node_start", node_type="HOTKEY", args=str(keys), line=node.line)
        self._log(f"HOTKEY: {keys}")
        self._call_action("hotkey", keys=keys, ctx=ctx)
        self._emit("node_done", node_type="HOTKEY", args=str(keys), line=node.line)

    def _exec_focus(self, node: ASTNode, ctx: ExecutionContext):
        title = self._interpolate(node.args)
        self._emit("node_start", node_type="FOCUS", args=title, line=node.line)
        self._log(f"FOCUS: {title}")
        self._call_action("focus_window", title=title, ctx=ctx)
        self._emit("node_done", node_type="FOCUS", args=title, line=node.line)

    def _exec_set(self, node: ASTNode, ctx: ExecutionContext):
        """SET var_name value — 设置变量"""
        parts = node.args.split(None, 1)
        if len(parts) >= 1:
            name = parts[0]
            value = self._interpolate(parts[1]) if len(parts) > 1 else ""
            self._set_var(name, value)
            self._log(f"SET {name} = {value}")

    def _exec_ocr_find(self, node: ASTNode, ctx: ExecutionContext):
        query = self._interpolate(node.args)
        self._emit("node_start", node_type="OCR_FIND", args=query, line=node.line)
        self._log(f"OCR_FIND: {query}")
        result = self._call_action("ocr_find", query=query, ctx=ctx)
        if isinstance(result, dict):
            self._set_var("_ocr_found", result.get("found", False))
            self._set_var("_ocr_text", result.get("text", ""))
            self._set_var("_ocr_x", result.get("center_x"))
            self._set_var("_ocr_y", result.get("center_y"))
            self._set_var("_ocr_confidence", result.get("confidence"))
        self._emit("node_done", node_type="OCR_FIND", args=query, line=node.line)

    def _exec_ocr_extract(self, node: ASTNode, ctx: ExecutionContext):
        self._emit("node_start", node_type="OCR_EXTRACT", args="", line=node.line)
        self._log("OCR_EXTRACT: 提取屏幕所有文字")
        result = self._call_action("ocr_extract", ctx=ctx)
        self._set_var("_ocr_texts", result)
        self._emit("node_done", node_type="OCR_EXTRACT", args="", line=node.line)

    def _exec_region_select(self, node: ASTNode, ctx: ExecutionContext):
        """REGION_SELECT var_name [message] — 用户交互式框选区域"""
        parts = node.args.split(None, 1)
        var_name = parts[0] if parts else "_selected_region"
        message = parts[1] if len(parts) > 1 else "请拖拽选择监控区域"
        self._emit("node_start", node_type="REGION_SELECT", args=var_name, line=node.line)
        self._log(f"REGION_SELECT: 请在屏幕框选区域 (变量={var_name})")
        result = self._call_action("region_select", message=message, ctx=ctx)
        if result:
            region_str = f"{result[0]},{result[1]},{result[2]},{result[3]}"
            self._set_var(var_name, region_str)
            self._set_var("_selected_region", region_str)
            self._log(f"  区域已选择: {region_str} → ${var_name}")
        else:
            self._set_var(var_name, "")
            self._set_var("_selected_region", "")
            self._log("  区域选择已取消")
        self._emit("node_done", node_type="REGION_SELECT", args=var_name, line=node.line)

    def _exec_image_find(self, node: ASTNode, ctx: ExecutionContext):
        """IMAGE_FIND template_name [AT x,y,w,h] — 图像模板匹配，设置变量"""
        args = self._interpolate(node.args)
        self._emit("node_start", node_type="IMAGE_FIND", args=args, line=node.line)
        self._log(f"IMAGE_FIND: {args}")
        result = self._call_action("image_find", args=args, ctx=ctx)
        if isinstance(result, dict):
            self._set_var("_image_found", result.get("found", False))
            self._set_var("_image_x", result.get("center_x"))
            self._set_var("_image_y", result.get("center_y"))
            self._set_var("_image_confidence", result.get("confidence"))
        self._emit("node_done", node_type="IMAGE_FIND", args=args, line=node.line)

    # ── 层次化 DSL 执行 ──────────────────────────────────────────
    def _exec_call(self, node: ASTNode, ctx: ExecutionContext):
        name = node.args
        if name not in self._subroutines:
            raise ExecutionError(f"未定义的子程序: '{name}'")

        if self._call_depth >= ctx.max_call_depth:
            raise ExecutionError(f"调用深度超过限制({ctx.max_call_depth}): '{name}'")
        self._call_depth += 1

        sub = self._subroutines[name]
        # 在调用者作用域中解析参数，绑定到子程序的参数名
        bindings = {}
        for i, param in enumerate(sub.params):
            if i < len(node.call_args):
                raw = node.call_args[i]
                resolved = self._interpolate(raw)
                bindings[param] = resolved
            else:
                bindings[param] = None

        self._push_scope(bindings)
        self._log(f"CALL {name}({', '.join(f'{k}={v}' for k, v in bindings.items())})")
        try:
            for child in sub.children:
                self._execute_node(child, ctx)
        except ReturnSignal as ret:
            self._log(f"  RETURN {sub.name} -> {ret.value}")
            return ret.value
        finally:
            self._pop_scope()
            self._call_depth -= 1

    def _exec_parallel(self, node: ASTNode, ctx: ExecutionContext):
        """PARALLEL 并行执行：每个分支独立线程"""
        branches = node.children
        if not branches:
            return
        self._log(f"PARALLEL: {len(branches)} 个分支并行执行")

        errors = []
        with ThreadPoolExecutor(max_workers=len(branches)) as pool:
            futures = {}
            for i, branch in enumerate(branches):
                future = pool.submit(self._execute_branch, branch, ctx, i)
                futures[future] = i

            for future in as_completed(futures):
                branch_idx = futures[future]
                try:
                    future.result()
                    self._log(f"  分支 {branch_idx} 完成")
                except Exception as e:
                    errors.append(f"分支 {branch_idx}: {e}")
                    self._log(f"  分支 {branch_idx} 失败: {e}")

        if errors:
            self._log(f"PARALLEL 完成，{len(errors)} 个分支有错误")

    def _execute_branch(self, node: ASTNode, ctx: ExecutionContext, branch_idx: int):
        """在线程池中执行一个并行分支"""
        for child in node.children:
            self._execute_node(child, ctx)

    def _exec_with(self, node: ASTNode, ctx: ExecutionContext):
        """WITH <handler_name> 异质执行：临时切换 action_handler"""
        handler_name = node.args
        handler = self._handlers.get(handler_name)
        if handler is None:
            self._log(f"  [WITH] 未知 handler '{handler_name}'，使用默认")
            for child in node.children:
                self._execute_node(child, ctx)
        else:
            old_handler = self._action_handler
            self._action_handler = handler
            self._log(f"  [WITH] 切换 handler 到 '{handler_name}'")
            try:
                for child in node.children:
                    self._execute_node(child, ctx)
            finally:
                self._action_handler = old_handler
                self._log(f"  [WITH] 恢复 handler 到默认")

    def _exec_import(self, node: ASTNode, ctx: ExecutionContext):
        path = node.args
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
        if not os.path.exists(path):
            raise ExecutionError(f"IMPORT 文件不存在: '{path}'")
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        parser = DSLParser()
        parser.parse(source)
        count = len(parser.subroutines)
        self._subroutines.update(parser.subroutines)
        self._log(f"IMPORT '{os.path.basename(path)}' ({count} 个子程序)")

    def _exec_when(self, node: ASTNode, ctx: ExecutionContext):
        """WHEN 事件注册：设置 watcher，不阻塞主流程"""
        try:
            from engine.triggers import get_trigger_engine, list_trigger_types
            engine = get_trigger_engine()
            if self._action_handler:
                engine.set_action_handler(self._action_handler)
            engine.set_executor(self)  # 传入 executor 引用，使触发器可复用 _execute_node

            event_key = node.event_key
            config_str = node.args

            # 查找注册的 trigger type 匹配 event_key
            trigger_types = list_trigger_types()
            matched = [t for t in trigger_types if t["event_key"] == event_key]
            if not matched:
                self._log(f"  [WHEN] 未知事件类型: {event_key}")
                return
            spec_name = matched[0]["name"]

            # 构建配置 dict
            config = {}
            recurring = False
            if event_key == "TIMER_INTERVAL":
                config["interval"] = float(config_str) if config_str else 10.0
                recurring = True
            elif config_str:
                config["path"] = config_str
                config["title"] = config_str
                config["name"] = config_str

            inst = engine.register(spec_name, config, node.children, recurring=recurring)
            self._log(f"  [WHEN] {event_key} 已注册 (id={inst.id})")
        except Exception as e:
            self._log(f"  [WHEN] 注册失败: {e}")

    # ── 动作调用 ─────────────────────────────────────────────────
    def _call_action(self, action: str, **kwargs) -> Any:
        with self._action_lock:
            if self._action_handler is None:
                self._log(f"  [模拟] {action}({kwargs})")
                return True
            retry_limit = kwargs.pop("retry_limit", 3)
            ctx = kwargs.pop("ctx", None)
            retry_limit = ctx.retry_limit if ctx else retry_limit
            last_err = None
            for attempt in range(1, retry_limit + 1):
                try:
                    if ctx is not None:
                        kwargs["ctx"] = ctx
                    return self._action_handler(action, **kwargs)
                except Exception as e:
                    last_err = e
                    self._log(f"  [重试 {attempt}/{retry_limit}] {action} 失败: {e}")
                    time.sleep(0.5 * attempt)
            # 所有重试失败 → 启动自愈管道
            return self._heal_action(action, kwargs, last_err, ctx)

    def _heal_action(self, action: str, context: dict, error: Exception,
                     ctx: Optional[ExecutionContext]) -> Any:
        """使用自愈管道尝试恢复"""
        self._log(f"  [自愈] {action} 所有重试失败，尝试恢复策略...")
        try:
            from engine.healing import get_healing_pipeline
            pipeline = get_healing_pipeline(self._action_handler)
            heal_context = {
                "action": action,
                "target": context.get("target", ""),
                "region": context.get("region"),
                "error": str(error),
            }
            result = pipeline.heal(action, str(error), heal_context,
                                   retry_action=lambda c: self._action_handler(action, **c))
            if result.success:
                self._log(f"  [自愈] [{result.strategy}] 恢复成功")
                return result.result
            self._log(f"  [自愈] 所有策略失败: {result.error}")
        except Exception as heal_err:
            self._log(f"  [自愈] 管道异常: {heal_err}")
        raise ExecutionError(f"动作 '{action}' 在重试和自愈后失败: {error}")

    def _set_state(self, state: ExecutorState):
        self._state = state
        self._emit("state_change", state=state.value)

    def _log(self, msg: str):
        self._emit("log", message=msg)


class BreakLoop(Exception):
    """用于从 LOOP 内部跳出的控制流异常"""
    def __str__(self):
        return "BREAK 只能在 LOOP 内部使用"
