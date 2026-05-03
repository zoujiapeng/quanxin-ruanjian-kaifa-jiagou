"""
Lobster Python 后端服务器 v2
HTTP API 从功能注册表自动生成路由
新增功能 -> 注册到 registry -> /api/feature/<name> 自动可用
"""
from __future__ import annotations
import json, os, sys, time, uuid
from pathlib import Path

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit

sys.path.insert(0, str(Path(__file__).parent))

# 导入功能模块（import 即注册）
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
import features.trigger_features     # noqa
import features.ai_plan_features     # noqa
import features.plugin_features      # noqa

from features.registry import registry, FeatureCategory
from features.state import push_log, get_logs as _get_logs
from engine.dsl_parser import DSLParser
from engine.executor import DSLExecutor, ExecutionContext
from engine.scheduler import TaskScheduler

try:
    from interaction.actions import ActionHandler
    action_handler = ActionHandler()
    SIMULATION_MODE = False
    print("[OK] 真实模式")
except ImportError as e:
    action_handler = None
    SIMULATION_MODE = True
    print(f"[WARN] 模拟模式: {e}")

app = Flask(__name__)
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
executor = DSLExecutor(action_handler=action_handler)
scheduler = TaskScheduler(executor)
_current_dsl = ""  # 当前加载的 DSL，供热重载使用


def broadcast(event, data):
    socketio.emit(event, data)


executor.on("node_start",     lambda **kw: broadcast("node_highlight", {"event": "start", **kw}))
executor.on("node_done",      lambda **kw: broadcast("node_highlight", {"event": "done", **kw}))
executor.on("error",          lambda **kw: broadcast("exec_error", kw))
executor.on("state_change",   lambda **kw: broadcast("state_change", kw))
executor.on("log",            lambda **kw: (push_log(kw.get("message", "")), broadcast("log", kw))[1])
scheduler.start()


# ── 核心路由 ──────────────────────────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok", "simulation_mode": SIMULATION_MODE,
        "executor_state": executor.state.value,
        "features": len(registry.all()), "version": "2.0.0",
    })


@app.route("/api/registry")
def get_registry():
    fmt = request.args.get("format", "json")
    if fmt == "markdown":
        return Response(registry.export_claude_context(), mimetype="text/markdown")
    if fmt == "mcp":
        return jsonify({"tools": registry.export_mcp_tools()})
    if fmt == "openapi":
        return jsonify(registry.export_openapi())
    if fmt == "dsl":
        return Response(registry.export_dsl_reference(), mimetype="text/markdown")
    return jsonify([f.to_dict() for f in registry.all()])


@app.route("/api/features")
def list_features():
    cat_str = request.args.get("category", "")
    try:
        cat = FeatureCategory(cat_str) if cat_str else None
        feats = registry.by_category(cat) if cat else registry.all()
    except ValueError:
        feats = registry.all()
    return jsonify([f.to_dict() for f in feats])


@app.route("/api/feature/<feature_name>", methods=["POST", "GET"])
def call_feature(feature_name):
    spec = registry.get(feature_name)
    if spec is None:
        return jsonify({
            "success": False, "error": f"功能 '{feature_name}' 不存在",
            "available": [f.name for f in registry.all()],
        }), 404
    if request.method == "POST":
        kwargs = request.get_json(force=True, silent=True) or {}
    else:
        kwargs = dict(request.args)
    result = registry.execute_with_typed_params(spec.name, **kwargs)
    code = 200 if result.get("success") else 500
    return jsonify(result), code


@app.route("/api/dsl/parse", methods=["POST"])
def parse_dsl():
    try:
        ast = DSLParser.from_string(request.get_json(force=True, silent=True).get("dsl", ""))
        return jsonify({"success": True, "ast": ast.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/dsl/run", methods=["POST"])
def run_dsl():
    data = request.get_json(force=True, silent=True) or {}
    task_id = data.get("task_id") or str(uuid.uuid4())
    try:
        DSLParser.from_string(data.get("dsl", ""))
        scheduler.submit(task_id, data["dsl"])
        return jsonify({"success": True, "task_id": task_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/dsl/run-sync", methods=["POST"])
def run_dsl_sync():
    global _current_dsl
    data = request.get_json(force=True, silent=True) or {}
    source = data.get("dsl", "")
    if not source.strip():
        return jsonify({"success": False, "error": "DSL 内容为空"}), 400
    _current_dsl = source
    start = time.time()
    try:
        DSLParser.from_string(source)
        ctx = ExecutionContext(
            max_loops=data.get("max_loops", 10),
            retry_limit=data.get("retry_limit", 1),
            timeout=data.get("timeout", 30.0),
        )
        executor.run_dsl_sync(source, ctx=ctx)
        elapsed = round(time.time() - start, 2)
        return jsonify({
            "success": True, "state": executor.state.value, "elapsed": elapsed,
            "logs": _get_logs(200),
        })
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        return jsonify({
            "success": False, "error": str(e), "elapsed": elapsed,
            "logs": _get_logs(200),
        }), 400


@app.route("/api/logs")
def get_logs():
    count = request.args.get("count", 50, type=int)
    return jsonify({"logs": _get_logs(count)})


@app.route("/api/executor/pause", methods=["POST"])
def pause():
    executor.pause()
    return jsonify({"state": executor.state.value})


@app.route("/api/executor/resume", methods=["POST"])
def resume():
    executor.resume()
    return jsonify({"state": executor.state.value})


@app.route("/api/executor/stop", methods=["POST"])
def stop():
    executor.stop()
    return jsonify({"state": executor.state.value})


@app.route("/api/executor/status")
def status():
    return jsonify({
        "state": executor.state.value,
        "queue": scheduler.get_queue_status(),
    })


@app.route("/api/dsl/state")
def dsl_state():
    """返回当前 DSL 状态（供热重载前端使用）"""
    return jsonify({
        "dsl": _current_dsl,
        "executor_state": executor.state.value,
        "features": len(registry.all()),
    })


# ── WebSocket ────────────────────────────────────────────────────
@socketio.on("connect")
def on_connect():
    emit("connected", {
        "msg": "Lobster v2", "simulation_mode": SIMULATION_MODE,
        "features": len(registry.all()),
    })


@socketio.on("run_dsl")
def on_run_dsl(data):
    task_id = str(uuid.uuid4())
    try:
        DSLParser.from_string(data.get("dsl", ""))
        scheduler.submit(task_id, data["dsl"])
        emit("task_submitted", {"task_id": task_id})
    except Exception as e:
        emit("exec_error", {"error": str(e)})


@socketio.on("call_feature")
def on_call_feature(data):
    name = data.pop("feature", "")
    emit("feature_result", registry.execute(name, **data))


@socketio.on("dsl_update")
def on_dsl_update(data):
    """DSL 热重载：客户端推送新 DSL，服务端解析校验并广播结果"""
    global _current_dsl
    dsl = data.get("dsl", "")
    _current_dsl = dsl
    try:
        ast = DSLParser.from_string(dsl)
        emit("dsl_update_ok", {
            "dsl": dsl,
            "ast": ast.to_dict(),
            "node_count": _count_nodes(ast),
        })
        broadcast("dsl_updated", {"dsl": dsl, "node_count": _count_nodes(ast)})
    except Exception as e:
        emit("dsl_update_error", {"error": str(e), "dsl": dsl})


@socketio.on("dsl_parse_validate")
def on_dsl_parse_validate(data):
    """DSL 解析校验：只解析不执行，返回 AST"""
    dsl = data.get("dsl", "")
    try:
        ast = DSLParser.from_string(dsl)
        emit("dsl_parse_result", {
            "valid": True,
            "ast": ast.to_dict(),
            "node_count": _count_nodes(ast),
        })
    except Exception as e:
        emit("dsl_parse_result", {"valid": False, "error": str(e)})


def _count_nodes(node) -> int:
    """递归计算 AST 节点数"""
    count = 1
    for child in getattr(node, "children", []):
        count += _count_nodes(child)
    for child in getattr(node, "else_children", []):
        count += _count_nodes(child)
    return count


# ── 启动 ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("LOBSTER_PORT", "7788"))
    total = len(registry.all())
    print(f"\nLobster v2 | Port:{port} | Features:{total} | {'SIMULATE' if SIMULATION_MODE else 'REAL'}\n")
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
