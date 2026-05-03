"""
DSL 执行功能注册
lobster_run_dsl / lobster_run_dsl_sync — 让 Claude Code 通过 MCP 直接执行 DSL
核心价值：一次性生成 DSL → 本地引擎循环执行，LOOP/WAIT/IF 不消耗 token
"""
from __future__ import annotations
import json

from features.registry import feature, P, TC, FeatureCategory as F

# 注意：这个文件只注册功能规格，实际执行逻辑在 engine/executor.py
# MCP Server 会本地执行这两个功能（不代理到后端），实现免 token 执行


@feature(
    name="run_dsl",
    display_name="执行 DSL",
    description="【免 token 执行】执行 Lobster DSL 脚本。CLI/MCP 生成 DSL 后调用此功能在本地引擎运行，LOOP/WAIT/IF 等控制流不消耗 Claude API token。返回执行日志。适用于：已生成完整 DSL 需要执行的场景。搭配：ai_generate_dsl（生成 DSL）、dsl_to_graph（可视化）",
    category=F.CONTROL,
    params=[
        P("dsl", "str", "DSL 脚本内容，多行文本", example="CLICK 开始\nWAIT 2\nCLICK 确认"),
        P("task_id", "str", "任务ID（可选，自动生成）", required=False, default=""),
        P("max_loops", "int", "最大循环次数", required=False, default=100),
        P("timeout", "number", "超时秒数", required=False, default=60),
    ],
    returns="dict{task_id, state, success} - 执行结果",
    dsl_keyword=None,
    examples=[
        "lobster call run_dsl dsl='CLICK 开始\\nWAIT 2\\nCLICK 确认'",
    ],
    test_cases=[
        TC("simple_click", {"dsl": "CLICK test"}, "success", skip_in_ci=True),
    ],
    tags=["core", "dsl", "execution"],
)
def run_dsl(dsl: str, task_id: str = "", max_loops: int = 100, timeout: float = 60) -> dict:
    """由 engine/executor.py 实际执行，此函数仅占位"""
    # 实际执行由 DSLExecutor 完成（server.py 和 mcp/server.py 各自持有 executor 实例）
    raise RuntimeError("run_dsl 需要通过 executor 执行，不能直接调用 handler")


@feature(
    name="run_dsl_sync",
    display_name="同步执行 DSL",
    description="【免 token 执行】同步执行 DSL 并等待完成。与 run_dsl 区别：阻塞直到执行完毕返回所有日志。适用于：短流程、需要获取完整执行结果的场景。搭配：run_dsl（异步长流程）",
    category=F.CONTROL,
    params=[
        P("dsl", "str", "DSL 脚本内容", example="CLICK 开始\nWAIT 完成"),
        P("max_loops", "int", "最大循环次数", required=False, default=10),
        P("retry_limit", "int", "失败重试次数", required=False, default=1),
        P("timeout", "number", "单步超时秒数", required=False, default=30),
    ],
    returns="dict{success, logs, elapsed} - 执行结果和日志",
    dsl_keyword=None,
    examples=[
        "lobster call run_dsl_sync dsl='CLICK 开始\\nWAIT 完成'",
    ],
    test_cases=[
        TC("simple_dsl", {"dsl": "CLICK test"}, "success", skip_in_ci=True),
    ],
    tags=["core", "dsl", "execution"],
)
def run_dsl_sync(dsl: str, max_loops: int = 10, retry_limit: int = 1, timeout: float = 30) -> dict:
    """由 engine/executor.py 实际执行，此函数仅占位"""
    raise RuntimeError("run_dsl_sync 需要通过 executor 执行，不能直接调用 handler")
