"""
新增功能模板
复制此文件到 features/ 目录，按需修改

3 步走:
1. 复制并重命名此文件
2. 填写 @feature(...) 元数据
3. 实现函数体

完成后自动获得:
- MCP 工具
- CLI `lobster call <name>` 可调用
- HTTP POST /api/feature/<name>
- 测试用例可通过 `lobster test` 运行
"""
from features.registry import feature, registry, P, TC, FeatureCategory as F


# ── 示例1: 简单动作功能 ───────────────────────────────────────────
@feature(
    name="my_simple_action",
    display_name="我的简单动作",
    description="功能描述",
    category=F.ACTION,
    params=[
        P("target", "str", "目标元素", example="开始按钮"),
        P("timeout", "number", "超时秒数", required=False, default=10),
    ],
    returns="bool - 是否成功",
    dsl_keyword="MY_ACTION",
    dsl_template="MY_ACTION {target}",
    examples=["MY_ACTION 开始按钮"],
    test_cases=[
        TC("basic", {"target": "test"}, "bool_true", skip_in_ci=True),
        TC("empty", {"target": ""}, "success"),
    ],
)
def my_simple_action(target: str, timeout: float = 10) -> bool:
    """实现逻辑"""
    # from interaction.actions import ActionHandler
    # handler = ActionHandler()
    # return handler.clicker.click(target, timeout=timeout)
    return True


# ── 示例2: 感知类功能 ─────────────────────────────────────────────
@feature(
    name="my_perception",
    display_name="我的感知功能",
    description="从屏幕提取信息",
    category=F.PERCEPTION,
    params=[
        P("region", "str", "区域 'x,y,w,h'", required=False, default=""),
    ],
    returns="dict{found, value}",
)
def my_perception(region: str = "") -> dict:
    return {"found": False, "value": None}
