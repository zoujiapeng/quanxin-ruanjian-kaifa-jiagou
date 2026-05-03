"""
Lobster MCP Server v2 — 自给自足版
从功能注册表动态生成 MCP 工具，自带 DSL 执行器

核心设计：
- 所有功能通过 registry 执行（本地或代理到后端）
- run_dsl / run_dsl_sync 本地执行（免 token）
- 后端可用时自动代理其余功能，不可用时降级
"""
from __future__ import annotations
import json, os, sys, time, traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 导入所有功能模块（触发注册）
import features.action_features      # noqa
import features.perception_features  # noqa
import features.ai_debug_features    # noqa
import features.system_features      # noqa
import features.dsl_features         # noqa
import features.browser_features     # noqa
import features.input_features       # noqa
import features.window_features      # noqa
import features.system_control_features  # noqa
import features.clipboard_features   # noqa
import features.network_features     # noqa
import features.timer_features       # noqa
import features.filedialog_features  # noqa
import features.a11y_features        # noqa
import features.macro_features       # noqa
import features.multimedia_features  # noqa
import features.fusion_features      # noqa
import features.persistence_features # noqa
import features.healing_features     # noqa

from features.registry import registry
from engine.dsl_parser import DSLParser
from engine.executor import DSLExecutor, ExecutionContext

BACKEND_URL = os.getenv("LOBSTER_URL", "http://localhost:7788")
HAS_REQUESTS = True
try:
    import requests
except ImportError:
    HAS_REQUESTS = False

# ── 本地 DSL 执行器（免 token 关键组件）─────────────────────────────
_action_handler = None
try:
    from interaction.actions import ActionHandler
    _action_handler = ActionHandler()
except ImportError:
    pass

_executor = DSLExecutor(action_handler=_action_handler)
_has_local_executor = _action_handler is not None


# ── 工具处理 ──────────────────────────────────────────────────────

def handle_tool_call(name: str, arguments: dict) -> str:
    """处理 MCP tools/call"""
    feature_name = name
    if name.startswith("lobster_"):
        feature_name = name[8:]

    # ── DSL 执行（本地，免 token） ──
    if feature_name == "run_dsl":
        return _exec_run_dsl(arguments)
    if feature_name == "run_dsl_sync":
        return _exec_run_dsl_sync(arguments)

    # ── 本地可执行的功能（不依赖后端） ──
    local_features = {
        "debug_list_features", "debug_validate_dsl", "debug_system_info",
        "debug_run_tests", "debug_get_logs", "debug_generate_test_flow",
        "dsl_to_graph", "graph_to_dsl", "parse_dsl",
    }
    if feature_name in local_features:
        result = registry.execute(feature_name, **arguments)
        return _format_result(result)

    # ── 后端代理 ──
    return _proxy_to_backend(feature_name, arguments)


def _exec_run_dsl(args: dict) -> str:
    """本地执行 DSL（异步提交，立即返回 task_id）"""
    dsl = args.get("dsl", "")
    if not dsl.strip():
        return "错误: DSL 内容为空"
    try:
        DSLParser.from_string(dsl)  # 语法验证
        task_id = args.get("task_id") or str(uuid4_short())
        ctx = ExecutionContext(
            max_loops=args.get("max_loops", 100),
            timeout=args.get("timeout", 60),
        )
        _executor.run_dsl(dsl, ctx=ctx)
        return json.dumps({"success": True, "task_id": task_id, "state": "running"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


def _exec_run_dsl_sync(args: dict) -> str:
    """本地执行 DSL（同步，等待完成）"""
    dsl = args.get("dsl", "")
    if not dsl.strip():
        return "错误: DSL 内容为空"
    start = time.time()
    try:
        DSLParser.from_string(dsl)
        ctx = ExecutionContext(
            max_loops=args.get("max_loops", 10),
            retry_limit=args.get("retry_limit", 1),
            timeout=args.get("timeout", 30),
        )
        _executor.run_dsl_sync(dsl, ctx=ctx)
        elapsed = round(time.time() - start, 2)
        return json.dumps({
            "success": True, "state": _executor.state.value,
            "elapsed": elapsed,
        }, ensure_ascii=False)
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        return json.dumps({
            "success": False, "error": str(e), "elapsed": elapsed,
        }, ensure_ascii=False)


def _format_result(result: dict) -> str:
    if result.get("success"):
        r = result.get("result", "")
        if isinstance(r, (dict, list)):
            return json.dumps(r, ensure_ascii=False, indent=2)
        return str(r)
    return f"错误: {result.get('error', '未知')}"


def _proxy_to_backend(feature_name: str, arguments: dict) -> str:
    if not HAS_REQUESTS:
        return "需要安装 requests 库: pip install requests"
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/feature/{feature_name}",
            json=arguments, timeout=30,
        )
        data = resp.json()
        if data.get("success"):
            r = data.get("result", "")
            if isinstance(r, (dict, list)):
                return json.dumps(r, ensure_ascii=False, indent=2)
            return str(r)
        return f"错误: {data.get('error', '未知')}"
    except requests.exceptions.ConnectionError:
        return f"无法连接后端 ({BACKEND_URL})"
    except Exception as e:
        return f"请求失败: {e}"


def _build_tools_list() -> list[dict]:
    """构造 MCP tools 列表（registry 已包含 DSL 执行工具）"""
    return registry.export_mcp_tools()


# ── MCP stdio 协议 ────────────────────────────────────────────────

def _read_message() -> dict | None:
    content_length = 0
    while True:
        line = sys.stdin.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            break
        if line.lower().startswith("content-length:"):
            try:
                content_length = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
    if content_length <= 0:
        return None
    raw = sys.stdin.read(content_length)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _send_message(msg: dict):
    payload = json.dumps(msg, ensure_ascii=False)
    data = f"Content-Length: {len(payload.encode('utf-8'))}\r\n\r\n{payload}"
    sys.stdout.write(data)
    sys.stdout.flush()


def uuid4_short() -> str:
    """简短唯一 ID"""
    import uuid
    return uuid.uuid4().hex[:12]


def serve():
    """主循环"""
    tools_cache = None

    while True:
        msg = _read_message()
        if msg is None:
            break

        method = msg.get("method", "")
        msg_id = msg.get("id")
        params = msg.get("params", {})

        if msg_id is None:
            continue

        if method == "initialize":
            _send_message({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "lobster-mcp", "version": "2.0.0"},
                },
            })

        elif method == "tools/list":
            if tools_cache is None:
                tools_cache = _build_tools_list()
            _send_message({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {"tools": tools_cache},
            })

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            try:
                text = handle_tool_call(tool_name, arguments)
                _send_message({
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {"content": [{"type": "text", "text": text}]},
                })
            except Exception as e:
                _send_message({
                    "jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32603, "message": str(e)},
                })

        elif method == "ping":
            _send_message({"jsonrpc": "2.0", "id": msg_id, "result": {}})

        else:
            _send_message({"jsonrpc": "2.0", "id": msg_id, "result": {}})


def main():
    serve()


if __name__ == "__main__":
    main()
