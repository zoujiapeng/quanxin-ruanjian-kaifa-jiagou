"""
Lobster 插件示例
本文件展示如何开发外部功能插件。
使用 `lobster call plugin_load path="plugins/example_plugin.py"` 加载
"""
from features.registry import feature, P, TC, FeatureCategory as F


@feature(
    name="example_hello",
    display_name="示例问候",
    description="【插件示例】一个简单的插件功能，返回问候消息。用于验证插件加载机制",
    category=F.DEBUG,
    params=[
        P("name", "str", "你的名字", example="世界"),
    ],
    returns="str - 问候消息",
)
def example_hello(name: str) -> str:
    return f"你好, {name}! 来自 Lobster 插件的问候。"


@feature(
    name="example_calc",
    display_name="示例计算器",
    description="【插件示例】一个简单的计算功能。用于展示带参数的插件功能",
    category=F.DEBUG,
    params=[
        P("a", "number", "第一个数字", example=10),
        P("b", "number", "第二个数字", example=20),
        P("op", "str", "运算符: add|sub|mul|div", required=False, default="add"),
    ],
    returns="dict{a, b, op, result} - 计算结果",
)
def example_calc(a: float, b: float, op: str = "add") -> dict:
    ops = {"add": lambda x, y: x + y, "sub": lambda x, y: x - y,
           "mul": lambda x, y: x * y, "div": lambda x, y: x / y if y else 0}
    result = ops.get(op, ops["add"])(a, b)
    return {"a": a, "b": b, "op": op, "result": result}
