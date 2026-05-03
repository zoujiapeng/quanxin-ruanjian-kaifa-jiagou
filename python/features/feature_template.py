"""
新增功能模板
复制此文件到 features/ 目录，按需修改

3 步走:
1. 复制并重命名此文件到 features/your_feature.py
2. 填写 @feature(...) 元数据
3. 实现函数体

完成后自动获得:
- MCP 工具: lobster_your_feature
- CLI 命令: lobster call your_feature --param value
- HTTP API: POST /api/feature/your_feature
- WebSocket: emit("call_feature", {feature: "your_feature", ...})
- 测试用例: lobster test 自动执行

无需修改任何其他文件！
"""
from features.registry import feature, registry, P, TC, FeatureCategory as F


# ── 示例1: 简单动作功能 ───────────────────────────────────────────
@feature(
    name="my_simple_action",
    display_name="我的简单动作",
    description="功能的详细描述，会显示在文档、MCP工具描述、CLI help中",
    category=F.ACTION,
    params=[
        P("target", "str", "目标元素", example="开始按钮"),
        P("timeout", "number", "超时秒数", required=False, default=10),
        P("enabled", "boolean", "是否启用", required=False, default=True),
    ],
    returns="bool - 是否成功",
    dsl_keyword="MY_ACTION",
    dsl_template="MY_ACTION {target}",
    examples=["MY_ACTION 开始按钮", "MY_ACTION 确认"],
    test_cases=[
        TC("basic", {"target": "test"}, "bool_true", skip_in_ci=True),
        TC("empty", {"target": ""}, "success"),
    ],
)
def my_simple_action(target: str, timeout: float = 10, enabled: bool = True) -> bool:
    """实现逻辑"""
    # from interaction.actions import ActionHandler
    # handler = ActionHandler()
    # return handler.clicker.click(target, timeout=timeout)
    return True


# ── 示例2: 感知类功能（返回数据而非bool）─────────────────────────
@feature(
    name="my_perception",
    display_name="我的感知功能",
    description="从屏幕提取某类信息",
    category=F.PERCEPTION,
    params=[
        P("region", "str", "区域 'x,y,w,h'", required=False, default=""),
    ],
    returns="dict{found, value, ...} - 识别结果",
    test_cases=[
        TC("full_screen", {}, "non_null"),
    ],
)
def my_perception(region: str = "") -> dict:
    """实现感知逻辑"""
    return {"found": False, "value": None}


# ── 示例3: 宏功能（组合多个步骤）─────────────────────────────────
@feature(
    name="my_macro",
    display_name="我的宏",
    description="执行完整的组合操作流程",
    category=F.MACRO,
    params=[
        P("loop_count", "number", "重复次数", required=False, default=1),
    ],
    returns="dict{success, steps_completed}",
    dsl_keyword="RUN",
    dsl_template="RUN my_macro",
    examples=["RUN my_macro"],
    test_cases=[
        TC("single_run", {"loop_count": 1}, "success", skip_in_ci=True),
    ],
)
def my_macro(loop_count: int = 1) -> dict:
    """调用其他已注册功能组合成宏"""
    steps = 0
    for i in range(loop_count):
        r = registry.execute("click_target", target="开始")
        if r["success"]:
            steps += 1
    return {"success": True, "steps_completed": steps}
