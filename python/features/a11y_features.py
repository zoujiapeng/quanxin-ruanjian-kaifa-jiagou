"""
无障碍树功能注册（待完善）
Windows Accessibility Tree 获取和操作
"""
from features.registry import feature, P, TC, FeatureCategory as F


@feature(
    name="a11y_get_tree",
    display_name="获取无障碍树",
    description="【无障碍】获取当前活动窗口的无障碍访问树结构。用于了解界面元素层次结构，比 OCR 更精确",
    category=F.PERCEPTION,
    params=[
        P("max_depth", "int", "最大深度", required=False, default=5),
        P("filter_visible", "boolean", "是否只返回可见元素", required=False, default=True),
    ],
    returns="dict{role, name, children} - 无障碍树",
    tags=["待完善"],
)
def a11y_get_tree(max_depth: int = 5, filter_visible: bool = True) -> dict:
    return {"implemented": False, "description": "获取无障碍树"}


@feature(
    name="a11y_find_element",
    display_name="查找无障碍元素",
    description="【无障碍】在无障碍树中查找匹配指定条件的 UI 元素。用于精确定位按钮、输入框等控件",
    category=F.PERCEPTION,
    params=[
        P("name", "str", "元素名称（模糊匹配）", example="发送"),
        P("role", "str", "元素角色（如 button, edit, list）", required=False, default=""),
        P("control_type", "str", "控件类型（如 Edit, Button, ComboBox）", required=False, default=""),
    ],
    returns="list[dict{name, role, bounds, enabled}] - 匹配元素列表",
    tags=["待完善"],
)
def a11y_find_element(name: str, role: str = "", control_type: str = "") -> list:
    return {"implemented": False, "description": "查找无障碍元素"}


@feature(
    name="a11y_click_element",
    display_name="点击无障碍元素",
    description="【无障碍】通过无障碍接口点击指定 UI 元素，绕过坐标/图像匹配。适用于标准 Windows 控件",
    category=F.ACTION,
    params=[
        P("name", "str", "元素名称", example="确定"),
        P("role", "str", "元素角色（可选）", required=False, default=""),
    ],
    returns="bool - 是否点击成功",
    tags=["待完善"],
)
def a11y_click_element(name: str, role: str = "") -> bool:
    return {"implemented": False, "description": "通过无障碍接口点击元素"}
