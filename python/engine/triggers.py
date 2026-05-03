"""
反应式事件引擎 — Trigger 定义、监控线程、执行回调
支持: 文件系统 / 进程 / 窗口 / 剪贴板 / 网络 事件
"""
from __future__ import annotations
import os
import time
import json
import threading
import logging
from pathlib import Path
from typing import Any, Callable, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger("lobster.triggers")


class TriggerCategory(str, Enum):
    FILESYSTEM = "filesystem"
    PROCESS = "process"
    WINDOW = "window"
    CLIPBOARD = "clipboard"
    NETWORK = "network"
    TIMER = "timer"


@dataclass
class TriggerSpec:
    """触发器的定义（类似 FeatureSpec）"""
    name: str
    display_name: str
    description: str
    category: TriggerCategory
    params: list
    event_key: str = ""  # 用于 DSL WHEN 语法的关键词


@dataclass
class TriggerInstance:
    """运行中的触发器实例"""
    id: str
    spec_name: str
    config: dict
    handler_actions: list  # AST 子节点列表
    status: str = "running"  # running | paused | stopped | fired
    fired_count: int = 0
    created_at: float = 0.0
    last_fired: float = 0.0
    recurring: bool = False  # 触发后是否重新布防（用于定时器）
    _thread: Optional[threading.Thread] = None
    _stop_event: threading.Event = field(default_factory=threading.Event)


# ── 装饰器（触发类型注册） ──────────────────────────────────────

_TRIGGER_TYPES: dict[str, TriggerSpec] = {}
_TRIGGER_INSTANCES: dict[str, TriggerInstance] = {}
_instances_lock = threading.Lock()


def trigger_type(name: str, display_name: str, description: str,
                 category: TriggerCategory, params: list,
                 event_key: str = "") -> Callable:
    """注册触发器类型"""
    def decorator(fn):
        spec = TriggerSpec(
            name=name, display_name=display_name, description=description,
            category=category, params=params, event_key=event_key,
        )
        _TRIGGER_TYPES[name] = spec
        fn._trigger_spec = spec
        return fn
    return decorator


def list_trigger_types() -> list[dict]:
    return [{
        "name": s.name, "display_name": s.display_name,
        "description": s.description, "category": s.category.value,
        "event_key": s.event_key,
        "params": [{"name": p[0], "type": p[1], "description": p[2]} for p in s.params],
    } for s in _TRIGGER_TYPES.values()]


# ── 触发引擎核心 ────────────────────────────────────────────────

class TriggerEngine:
    """
    触发引擎: 管理 watcher 线程和回调

    每个 WHEN 语句注册一个 TriggerInstance,
    TriggerEngine 为其创建 watcher 线程,
    条件满足时执行 handler 动作序列
    """

    def __init__(self):
        self._action_handler = None
        self._executor = None  # DSLExecutor 引用，由 set_executor 设置
        self._instance_counter = 0
        self._instance_lock = threading.Lock()

    def set_action_handler(self, handler):
        self._action_handler = handler

    def set_executor(self, executor):
        """设置 DSLExecutor 引用，用于 handler 动作执行"""
        self._executor = executor

    def register(self, spec_name: str, config: dict,
                 handler_actions: list,
                 recurring: bool = False) -> TriggerInstance:
        """注册一个触发器实例并启动监控"""
        spec = _TRIGGER_TYPES.get(spec_name)
        if not spec:
            raise ValueError(f"未知触发器类型: '{spec_name}'")

        self._instance_counter += 1
        inst = TriggerInstance(
            id=f"trg_{int(time.time())}_{self._instance_counter}",
            spec_name=spec_name,
            config=config,
            handler_actions=handler_actions,
            created_at=time.time(),
            recurring=recurring,
        )
        inst._stop_event = threading.Event()

        # 启动监控线程
        watcher_fn = _WATCHER_FUNCTIONS.get(spec_name)
        if watcher_fn:
            inst._thread = threading.Thread(
                target=self._watcher_loop,
                args=(inst, spec, watcher_fn),
                daemon=True,
                name=f"trigger-{inst.id}",
            )
            inst._thread.start()
        else:
            logger.warning(f"触发器 '{spec_name}' 没有 watcher 实现")

        with _instances_lock:
            _TRIGGER_INSTANCES[inst.id] = inst
        return inst

    def _watcher_loop(self, inst: TriggerInstance, spec: TriggerSpec,
                      watcher_fn: Callable):
        """Watcher 线程主循环"""
        logger.info(f"[trigger] 启动 {spec.name}: {inst.config}")
        while not inst._stop_event.is_set():
            try:
                fired = watcher_fn(inst.config, inst._stop_event)
                if fired:
                    inst.fired_count += 1
                    inst.last_fired = time.time()
                    inst.status = "fired"
                    self._execute_handler(inst)
                    if inst.recurring:
                        inst.status = "running"
                        continue
                    inst.status = "stopped"
                    break
            except Exception as e:
                logger.error(f"[trigger] {inst.id} 错误: {e}")
                time.sleep(1)
        logger.info(f"[trigger] 停止 {spec.name}: {inst.id}")

    def _execute_handler(self, inst: TriggerInstance):
        """当触发器条件满足时，执行 handler 动作序列"""
        if self._executor:
            from engine.executor import ExecutionContext
            ctx = ExecutionContext(max_loops=10, timeout=30)
            for node in inst.handler_actions:
                try:
                    self._executor._execute_node(node, ctx)
                except Exception as e:
                    logger.error(f"[trigger] handler 执行失败: {e}")
        elif self._action_handler:
            logger.info(f"[trigger] 触发 {inst.id} (无 executor，使用直接 handler)")
            # 简单降级：直接调用 action_handler 处理基本节点
            self._execute_handler_direct(inst)
        else:
            logger.info(f"[trigger] 触发 {inst.id} (模拟模式，不执行)")

    def _execute_handler_direct(self, inst: TriggerInstance):
        """降级方案：没有 executor 时直接调用 action_handler"""
        from engine.dsl_parser import NodeType
        for node in inst.handler_actions:
            try:
                nt = node.type
                if nt == NodeType.SEQUENCE:
                    for c in node.children:
                        self._action_handler("click", target=c.args)
                elif nt == NodeType.CLICK:
                    self._action_handler("click", target=node.args)
                elif nt == NodeType.WAIT:
                    self._action_handler("wait", condition=node.args, timeout=10)
                elif nt == NodeType.TYPE:
                    self._action_handler("type", text=node.args)
            except Exception as e:
                logger.error(f"[trigger] handler 直接执行失败: {e}")

    def stop(self, instance_id: str) -> bool:
        """停止一个触发器实例"""
        with _instances_lock:
            inst = _TRIGGER_INSTANCES.get(instance_id)
            if not inst:
                return False
            inst._stop_event.set()
            inst.status = "stopped"
        return True

    def stop_all(self):
        """停止所有触发器"""
        with _instances_lock:
            for inst in _TRIGGER_INSTANCES.values():
                if inst.status == "running":
                    inst._stop_event.set()
                    inst.status = "stopped"

    def get_instance(self, instance_id: str) -> Optional[dict]:
        with _instances_lock:
            inst = _TRIGGER_INSTANCES.get(instance_id)
            if not inst:
                return None
            return {
                "id": inst.id,
                "spec_name": inst.spec_name,
                "config": inst.config,
                "status": inst.status,
                "fired_count": inst.fired_count,
                "created_at": inst.created_at,
                "last_fired": inst.last_fired,
            }

    def list_instances(self) -> list[dict]:
        with _instances_lock:
            return [{
                "id": inst.id,
                "spec_name": inst.spec_name,
                "config": inst.config,
                "status": inst.status,
                "fired_count": inst.fired_count,
                "created_at": inst.created_at,
            } for inst in _TRIGGER_INSTANCES.values()]


# ── Watcher 函数实现 ────────────────────────────────────────────

def _watch_file_created(config: dict, stop: threading.Event) -> bool:
    """监控文件创建"""
    path = config.get("path", "")
    watched_dir = os.path.dirname(path) or "."
    pattern = os.path.basename(path)
    known = set(os.listdir(watched_dir)) if os.path.isdir(watched_dir) else set()
    poll = config.get("interval", 0.5)
    while not stop.is_set():
        time.sleep(poll)
        if not os.path.isdir(watched_dir):
            continue
        current = set(os.listdir(watched_dir))
        new_files = current - known
        for f in new_files:
            if pattern == "*" or pattern in f or f.endswith(pattern.replace("*", "")):
                known = current
                return True
        known = current
    return False


def _watch_process_exit(config: dict, stop: threading.Event) -> bool:
    """监控进程退出（进程存在时轮询，消失时触发）"""
    name = config.get("name", "").lower()
    poll = config.get("interval", 0.5)
    try:
        import psutil
        while not stop.is_set():
            found = False
            for proc in psutil.process_iter(["name"]):
                try:
                    if proc.info["name"] and proc.info["name"].lower() == name:
                        found = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            if not found:
                return True
            time.sleep(poll)
    except ImportError:
        import subprocess
        while not stop.is_set():
            try:
                out = subprocess.check_output(f"tasklist /fi \"IMAGENAME eq {name}\"", shell=True, text=True)
                if name not in out or "No tasks" in out:
                    return True
            except Exception:
                return True
            time.sleep(poll)
    return False


def _watch_process_start(config: dict, stop: threading.Event) -> bool:
    """监控进程启动"""
    name = config.get("name", "").lower()
    poll = config.get("interval", 0.5)
    try:
        import psutil
        while not stop.is_set():
            for proc in psutil.process_iter(["name"]):
                try:
                    if proc.info["name"] and proc.info["name"].lower() == name:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            time.sleep(poll)
    except ImportError:
        # 降级: 使用 tasklist
        while not stop.is_set():
            import subprocess
            try:
                out = subprocess.check_output(f"tasklist /fi \"IMAGENAME eq {name}\"", shell=True, text=True)
                if name in out and "No tasks" not in out:
                    return True
            except Exception:
                pass
            time.sleep(poll)
    return False


def _watch_window_open(config: dict, stop: threading.Event) -> bool:
    """监控窗口打开"""
    title_pattern = config.get("title", "").lower()
    poll = config.get("interval", 0.3)
    while not stop.is_set():
        try:
            import win32gui
            def cb(hwnd, ctx):
                if win32gui.IsWindowVisible(hwnd):
                    wtitle = (win32gui.GetWindowText(hwnd) or "").lower()
                    if title_pattern in wtitle:
                        ctx["found"] = True
            ctx = {"found": False}
            win32gui.EnumWindows(cb, ctx)
            if ctx["found"]:
                return True
        except ImportError:
            pass
        time.sleep(poll)
    return False


def _watch_clipboard(config: dict, stop: threading.Event) -> bool:
    """监控剪贴板变化（简单轮询）"""
    try:
        import pyperclip
        old = pyperclip.paste()
        poll = config.get("interval", 0.3)
        while not stop.is_set():
            time.sleep(poll)
            try:
                current = pyperclip.paste()
                if current != old:
                    return True
            except Exception:
                pass
    except ImportError:
        time.sleep(3600)
    return False


def _watch_network(config: dict, stop: threading.Event) -> bool:
    """监控网络连接变化"""
    poll = config.get("interval", 1.0)
    import socket
    target = config.get("target", "8.8.8.8")
    port = config.get("port", 80)
    while not stop.is_set():
        try:
            s = socket.socket()
            s.settimeout(2)
            s.connect((target, port))
            s.close()
            return True
        except (OSError, socket.error):
            pass
        time.sleep(poll)
    return False


def _watch_timer_interval(config: dict, stop: threading.Event) -> bool:
    """定时器触发: 等待设定的间隔后返回 True"""
    interval = config.get("interval", 10.0)
    return not stop.wait(interval)  # interval 耗尽 → 触发；被停止 → 不触发


# Watcher 函数映射
_WATCHER_FUNCTIONS = {
    "file_created": _watch_file_created,
    "file_deleted": lambda c, s: _watch_file_created({**c, "wait_delete": True}, s),  # simplified
    "process_start": _watch_process_start,
    "process_exit": _watch_process_exit,
    "window_open": _watch_window_open,
    "clipboard_change": _watch_clipboard,
    "network_available": _watch_network,
    "timer_interval": _watch_timer_interval,
}


# ── 注册内置触发器类型 ──────────────────────────────────────────

@trigger_type(
    name="file_created", display_name="文件创建",
    description="监控文件或目录中出现新文件",
    category=TriggerCategory.FILESYSTEM, event_key="FILE_CREATED",
    params=[("path", "string", "文件路径/模式，如 C:/downloads/*.pdf"),
            ("interval", "number", "轮询间隔秒数")],
)
def _reg_file_created(): pass

@trigger_type(
    name="process_start", display_name="进程启动",
    description="监控指定名称的进程启动",
    category=TriggerCategory.PROCESS, event_key="PROCESS_START",
    params=[("name", "string", "进程名称，如 chrome.exe"),
            ("interval", "number", "轮询间隔秒数")],
)
def _reg_process_start(): pass

@trigger_type(
    name="process_exit", display_name="进程退出",
    description="监控指定名称的进程退出",
    category=TriggerCategory.PROCESS, event_key="PROCESS_EXIT",
    params=[("name", "string", "进程名称，如 chrome.exe"),
            ("interval", "number", "轮询间隔秒数")],
)
def _reg_process_exit(): pass

@trigger_type(
    name="window_open", display_name="窗口打开",
    description="监控包含指定标题的窗口打开",
    category=TriggerCategory.WINDOW, event_key="WINDOW_OPEN",
    params=[("title", "string", "窗口标题（模糊匹配）"),
            ("interval", "number", "轮询间隔秒数")],
)
def _reg_window_open(): pass

@trigger_type(
    name="clipboard_change", display_name="剪贴板变化",
    description="监控剪贴板内容变化",
    category=TriggerCategory.CLIPBOARD, event_key="CLIPBOARD_CHANGE",
    params=[("interval", "number", "轮询间隔秒数")],
)
def _reg_clipboard(): pass

@trigger_type(
    name="network_available", display_name="网络可用",
    description="监控网络连接变为可用",
    category=TriggerCategory.NETWORK, event_key="NETWORK_AVAILABLE",
    params=[("target", "string", "检测目标地址"),
            ("port", "number", "检测端口")],
)
def _reg_network(): pass

@trigger_type(
    name="timer_interval", display_name="定时器",
    description="按固定间隔定时触发，可循环",
    category=TriggerCategory.TIMER, event_key="TIMER_INTERVAL",
    params=[("interval", "number", "触发间隔秒数"),
            ("count", "number", "触发次数（0=无限）")],
)
def _reg_timer(): pass


# ── 全局单例 ────────────────────────────────────────────────────

_engine: Optional[TriggerEngine] = None


def get_trigger_engine() -> TriggerEngine:
    global _engine
    if _engine is None:
        _engine = TriggerEngine()
    return _engine
