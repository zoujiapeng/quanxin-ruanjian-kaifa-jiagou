"""
AI 规划执行功能注册
ai_plan_and_execute — 自主 Agent 闭环
"""
from features.registry import feature, P, TC, FeatureCategory as F, registry


@feature(
    name="ai_plan_and_execute",
    display_name="AI 规划执行",
    description="【AI 规划】接收自然语言目标，自主完成观察→规划→执行→反馈闭环。不需要 Claude Code 逐步骤干预。适用于复杂多步任务如「打开微信给张三发消息」「下载文件并保存到桌面」",
    category=F.AI,
    params=[
        P("goal", "str", "自然语言目标描述", example="打开微信给张三发消息"),
        P("api_key", "str", "Anthropic API Key（可选，默认使用环境变量）",
          required=False, default=""),
        P("max_iterations", "int", "最大规划迭代次数", required=False, default=10),
    ],
    returns="dict{success, steps, error} - 执行结果",
)
def ai_plan_and_execute(goal: str, api_key: str = "", max_iterations: int = 10) -> dict:
    try:
        from engine.planner import Planner
        planner = Planner(api_key=api_key)
        planner.set_registry(registry)
        return planner.plan_and_execute(goal, max_iterations=max_iterations)
    except ImportError as e:
        return {"success": False, "error": f"AI 规划模块不可用: {e}", "steps": []}


@feature(
    name="ai_plan_history",
    display_name="AI 规划历史",
    description="【AI 规划】查看最近一次 AI 规划执行的步骤历史。用于诊断规划执行过程",
    category=F.DEBUG,
    params=[],
    returns="list[dict{action, params, error, elapsed_ms}] - 执行步骤列表",
)
def ai_plan_history() -> list:
    try:
        from engine.planner import get_planner
        return get_planner().get_history()
    except ImportError:
        return []
