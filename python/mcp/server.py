"""
Lobster MCP Server
从功能注册表动态生成 MCP 工具
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 导入所有功能模块（触发注册）
import features.action_features      # noqa
import features.perception_features  # noqa
import features.ai_debug_features    # noqa
import features.system_features      # noqa

from features.registry import registry

BACKEND_URL = os.getenv("LOBSTER_URL", "http://localhost:7788")
HAS_REQUESTS = True
try:
    import requests
except ImportError:
    HAS_REQUESTS = False


# ── 工具处理 ──────────────────────────────────────────────────────

def handle_tool_call(name: str, arguments: dict) -> str:
    """处理 MCP tools/call"""
    # map: lobster_click_target -> click_target
    feature_name = name
    if name.startswith("lobster_"):
        feature_name = name[8:]

    # 本地可执行的功能（不依赖后端）
    if feature_name in ("debug_list_features",):
        result = registry.execute(feature_name, **arguments)
        return _format_result(result)

    if feature_name in ("debug_validate_dsl", "dsl_to_graph", "graph_to_dsl", "parse_dsl"):
        result = registry.execute(feature_name, **arguments)
        return _format_result(result)

    # 后端代理
    return _proxy_to_backend(feature_name, arguments)


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
                tools_cache = registry.export_mcp_tools()
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
