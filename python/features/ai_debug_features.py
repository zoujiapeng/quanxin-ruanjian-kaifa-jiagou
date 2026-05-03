"""
AI 规划 + 调试功能注册
DSL生成 / 流程图转换 / 自主调试 / 系统诊断
"""
import json
import os
import sys
import time
from typing import Optional

from features.registry import feature, registry, P, TC, FeatureCategory as F
from features.state import get_logs


# ═══════════════════════════════════════════════════════════════
# AI 生成 DSL
# ═══════════════════════════════════════════════════════════════
@feature(
    name="ai_generate_dsl",
    display_name="AI生成DSL",
    description="将自然语言任务描述转换为 Lobster DSL",
    category=F.AI,
    params=[
        P("task", "str", "自然语言任务描述", example="打开微信给张三发消息"),
        P("api_key", "str", "Anthropic API Key（可选，默认使用环境变量）",
          required=False, default=""),
        P("context", "str", "额外上下文（当前场景描述）", required=False, default=""),
    ],
    returns="dict{dsl, ast, input_tokens, output_tokens}",
    test_cases=[
        TC("basic_gen", {"task": "点击开始按钮", "api_key": ""},
           "success", validator=lambda r: r.get("success") is True),
    ],
)
def ai_generate_dsl(task: str, api_key: str = "", context: str = "") -> dict:
    key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    feature_ctx = _build_feature_context()

    system_prompt = f"""你是 Lobster 自动化系统的 DSL 规划引擎。
用一次响应生成完整的 DSL 执行计划。

可用 DSL 指令：
{feature_ctx}

规则：
- 只输出 DSL，不加任何解释或 markdown 代码块
- # 开头为注释
- 参数直接跟在指令后，空格分隔
- 优先使用文字匹配而非坐标

{('当前场景: ' + context) if context else ''}"""

    if not key:
        return {
            "dsl": f"# 模拟生成（无API Key）\n# 任务: {task}\nCLICK 开始\nWAIT 完成",
            "ast": None, "input_tokens": 0, "output_tokens": 0, "simulated": True,
        }

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": task}],
        )
        dsl = msg.content[0].text.strip()
        from engine.dsl_parser import DSLParser
        try:
            ast = DSLParser.from_string(dsl).to_dict()
        except Exception:
            ast = None
        return {
            "dsl": dsl, "ast": ast,
            "input_tokens": msg.usage.input_tokens,
            "output_tokens": msg.usage.output_tokens,
            "simulated": False,
        }
    except Exception as e:
        return {"dsl": "", "error": str(e), "simulated": False}


# ═══════════════════════════════════════════════════════════════
# DSL ↔ 流程图双向转换
# ═══════════════════════════════════════════════════════════════
@feature(
    name="dsl_to_graph",
    display_name="DSL转流程图",
    description="将 DSL 文本转换为 React Flow 兼容的节点/边 JSON",
    category=F.AI,
    params=[
        P("dsl", "str", "DSL文本", example="CLICK 开始\nWAIT 加载"),
        P("layout", "str", "布局: vertical|horizontal|auto", required=False, default="vertical"),
    ],
    returns="dict{nodes, edges}",
    test_cases=[
        TC("simple_dsl", {"dsl": "CLICK 开始\nWAIT 完成"}, "non_null",
           validator=lambda r: r["success"] and len(r["result"]["nodes"]) >= 2),
    ],
)
def dsl_to_graph(dsl: str, layout: str = "vertical") -> dict:
    from engine.dsl_parser import DSLParser, ASTNode, NodeType

    try:
        ast = DSLParser.from_string(dsl)
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}

    nodes, edges = [], []
    x_base = 300
    y_step = 90 if layout != "horizontal" else 0
    COLOR_MAP = {
        "CLICK": "#3b82f6", "WAIT": "#f59e0b", "LOOP": "#8b5cf6",
        "IF": "#ec4899", "RUN": "#ef4444", "SEQUENCE": "#22c55e",
    }
    counter = [0]

    def nid():
        counter[0] += 1
        return f"n_{counter[0]}"

    def add_node(nt, label, args, x, y):
        uid = nid()
        nodes.append({
            "id": uid, "type": "lobsterNode",
            "position": {"x": x, "y": y},
            "data": {"label": label, "nodeType": nt, "args": args,
                     "color": COLOR_MAP.get(nt, "#6b7280")},
        })
        return uid

    def add_edge(src, tgt, label="", animated=False):
        edges.append({
            "id": f"e_{src}_{tgt}", "source": src, "target": tgt,
            "label": label, "type": "smoothstep", "animated": animated,
        })

    start_id = add_node("START", "开始", "", x_base, 0)

    def walk(node: ASTNode, prev: str, y: int, x: int):
        if getattr(node.type, 'value', None) == 'SEQUENCE' or node.type == NodeType.SEQUENCE:
            last = prev
            for child in node.children:
                last, y = walk(child, last, y, x)
            return last, y

        y += y_step
        uid = add_node(str(node.type.value if hasattr(node.type, 'value') else node.type),
                       str(node.type.value if hasattr(node.type, 'value') else node.type),
                       node.args, x, y)
        add_edge(prev, uid, animated=(getattr(node.type, 'value', None) == 'LOOP'))

        if getattr(node.type, 'value', None) in ('LOOP', 'IF') and node.children:
            last_child, child_y = uid, y
            for child in node.children:
                last_child, child_y = walk(child, last_child, child_y, x + 60)
            if getattr(node.type, 'value', None) == 'IF' and node.else_children:
                else_last = uid
                else_y = y
                for child in node.else_children:
                    else_last, else_y = walk(child, else_last, else_y, x + 200)
            if getattr(node.type, 'value', None) == 'LOOP':
                add_edge(last_child, uid, label="loop", animated=True)
            return uid, max(child_y, y)
        return uid, y

    walk(ast, start_id, 0, x_base)
    return {"nodes": nodes, "edges": edges}


@feature(
    name="graph_to_dsl",
    display_name="流程图转DSL",
    description="将 React Flow 节点/边 JSON 转换回 DSL 文本",
    category=F.AI,
    params=[
        P("nodes", "string", "JSON字符串：节点数组"),
        P("edges", "string", "JSON字符串：边数组"),
    ],
    returns="str - DSL文本",
    test_cases=[
        TC("simple",
           {"nodes": '[{"id":"n1","data":{"nodeType":"CLICK","args":"开始"},"position":{"x":0,"y":0}}]',
            "edges": "[]"},
           "non_null", validator=lambda r: "CLICK" in str(r.get("result", ""))),
    ],
)
def graph_to_dsl(nodes: str, edges: str) -> str:
    try:
        nodes_data = json.loads(nodes) if isinstance(nodes, str) else nodes
    except Exception as e:
        return f"# 解析错误: {e}"

    valid = [n for n in nodes_data if n.get("data", {}).get("nodeType") not in ("START", "END", None)]
    valid.sort(key=lambda n: n.get("position", {}).get("y", 0))

    lines = ["# 由流程图生成的 DSL"]
    for n in valid:
        d = n.get("data", {})
        nt = d.get("nodeType", "")
        args = d.get("args", "").strip()
        if nt == "CONDITION":
            nt = "IF"
        elif nt == "MACRO":
            nt = "RUN"
        if nt in ("CLICK", "WAIT", "LOOP", "IF", "RUN", "SCROLL", "TYPE", "DRAG", "HOTKEY"):
            lines.append(f"{nt} {args}".strip())
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 调试功能
# ═══════════════════════════════════════════════════════════════
@feature(
    name="debug_get_logs",
    display_name="获取执行日志",
    description="返回执行器最近的日志",
    category=F.DEBUG,
    params=[
        P("count", "number", "日志条数", required=False, default=50),
    ],
    returns="list[dict{ts, msg}]",
)
def debug_get_logs(count: int = 50):
    return get_logs(count)


@feature(
    name="debug_run_tests",
    display_name="运行测试",
    description="运行所有注册功能的测试用例",
    category=F.DEBUG,
    params=[
        P("category", "str", "只测试指定类别（可选）", required=False, default=""),
        P("skip_ci", "boolean", "跳过需要真实屏幕的测试", required=False, default=True),
    ],
    returns="dict{passed, failed, skipped, details}",
    test_cases=[
        TC("self_test", {"category": "debug", "skip_ci": True}, "success",
           validator=lambda r: r["success"] and r["result"]["passed"] >= 0),
    ],
)
def debug_run_tests(category: str = "", skip_ci: bool = True) -> dict:
    cat = None
    if category:
        try:
            cat = F(category)
        except ValueError:
            pass
    return registry.run_tests(category=cat, skip_ci=skip_ci)


@feature(
    name="debug_list_features",
    display_name="列出功能",
    description="返回所有注册功能的完整信息",
    category=F.DEBUG,
    params=[
        P("category", "str", "过滤类别（可选）", required=False, default=""),
        P("format", "str", "输出格式: json|markdown|mcp", required=False, default="json"),
    ],
    returns="str or list - 功能列表",
    test_cases=[
        TC("list_all", {}, "non_null"),
        TC("list_json", {"format": "json"}, "non_null"),
        TC("list_md", {"format": "markdown"}, "non_null"),
    ],
)
def debug_list_features(category: str = "", format: str = "json"):
    cat = None
    if category:
        try:
            cat = F(category)
        except ValueError:
            pass
    features = registry.by_category(cat) if cat else registry.all()
    if format == "markdown":
        return registry.export_claude_context()
    elif format == "mcp":
        return registry.export_mcp_tools()
    return [f.to_dict() for f in features]


@feature(
    name="debug_validate_dsl",
    display_name="验证DSL语法",
    description="解析并验证 DSL 文本，返回 AST 和错误信息",
    category=F.DEBUG,
    params=[
        P("dsl", "str", "DSL文本", example="CLICK 开始\nWAIT 完成"),
    ],
    returns="dict{valid, ast, error}",
    test_cases=[
        TC("valid", {"dsl": "CLICK 开始\nWAIT 完成"}, "non_null",
           validator=lambda r: r["success"] and r["result"]["valid"]),
        TC("invalid", {"dsl": "INVALID_CMD arg"}, "success",
           validator=lambda r: r["success"] and not r["result"]["valid"]),
    ],
)
def debug_validate_dsl(dsl: str) -> dict:
    from engine.dsl_parser import DSLParser
    try:
        ast = DSLParser.from_string(dsl)
        return {"valid": True, "ast": ast.to_dict(), "error": None}
    except Exception as e:
        return {"valid": False, "ast": None, "error": str(e)}


@feature(
    name="debug_system_info",
    display_name="系统诊断",
    description="返回系统状态、依赖检查、功能统计",
    category=F.DEBUG,
    params=[],
    returns="dict - 系统诊断报告",
    test_cases=[TC("info", {}, "non_null")],
)
def debug_system_info() -> dict:
    deps = {}
    for pkg in ["pyautogui", "cv2", "pytesseract", "mss", "anthropic", "flask", "numpy"]:
        try:
            __import__(pkg)
            deps[pkg] = True
        except ImportError:
            deps[pkg] = False

    all_features = registry.all()
    cat_counts = {}
    for f in all_features:
        k = f.category.value
        cat_counts[k] = cat_counts.get(k, 0) + 1

    return {
        "python_version": sys.version,
        "platform": sys.platform,
        "total_features": len(all_features),
        "features_by_category": cat_counts,
        "dependencies": deps,
        "mcp_tools_count": len(registry.export_mcp_tools()),
        "test_cases_count": sum(len(f.test_cases) for f in all_features),
    }


@feature(
    name="debug_generate_test_flow",
    display_name="生成测试流程图",
    description="AI自主生成测试场景的DSL和流程图，用于验证系统功能",
    category=F.DEBUG,
    params=[
        P("scenario", "str", "测试场景描述", example="测试点击和等待功能"),
        P("api_key", "str", "API Key（可选）", required=False, default=""),
    ],
    returns="dict{dsl, graph, description}",
    test_cases=[
        TC("gen_test_flow", {"scenario": "基础点击测试"}, "success"),
    ],
)
def debug_generate_test_flow(scenario: str, api_key: str = "") -> dict:
    dsl_result = ai_generate_dsl(
        task=f"[测试场景] {scenario}\n要求：生成可验证功能的完整测试流程",
        api_key=api_key,
    )
    dsl = dsl_result.get("dsl", "CLICK 测试按钮\nWAIT 测试完成")
    graph = dsl_to_graph(dsl)
    return {
        "dsl": dsl,
        "graph": graph,
        "description": f"测试场景: {scenario}",
        "tokens_used": dsl_result.get("input_tokens", 0) + dsl_result.get("output_tokens", 0),
    }


# ── 内部工具 ──────────────────────────────────────────────────────
def _build_feature_context() -> str:
    lines = []
    for f in registry.all():
        if f.dsl_keyword:
            lines.append(f"{f.dsl_template} - {f.description}")
    lines += [
        "LOOP <标签> ... END - 循环执行子块",
        "IF <条件> ... [ELSE ...] END - 条件判断",
        "RUN <宏名称> - 执行内置宏",
        "WAIT <条件> - 等待: 文字:X / 图像:X / 稳定 / 变化 / 消失:X",
    ]
    return "\n".join(lines)
