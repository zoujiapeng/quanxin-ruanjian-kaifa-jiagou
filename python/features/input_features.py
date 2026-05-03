"""
高级输入功能注册（待完善）
右键 / 悬停 / 鼠标移动 / 连击 / 中键
"""
from features.registry import feature, P, TC, FeatureCategory as F


@feature(
    name="right_click",
    display_name="右键点击",
    description="【鼠标】在指定位置或目标上执行右键点击。用于打开右键菜单、触发上下文操作",
    category=F.ACTION,
    params=[
        P("target", "str", "目标：文字 / 坐标 'x,y' / 图像模板名", example="桌面"),
        P("region", "str", "搜索区域 'x,y,w,h'（可选）", required=False, default=""),
    ],
    returns="bool - 是否成功",
    tags=["待完善"],
)
def right_click(target: str, region: str = "") -> bool:
    return {"implemented": False, "description": "右键点击"}


@feature(
    name="hover",
    display_name="悬停",
    description="【鼠标】将鼠标悬停在目标上不点击。用于触发 tooltip、hover 效果或预览链接",
    category=F.ACTION,
    params=[
        P("target", "str", "悬停目标：文字 / 坐标 / 图像模板名", example="菜单项"),
        P("duration", "number", "悬停秒数", required=False, default=0.5),
    ],
    returns="bool - 是否成功",
    tags=["待完善"],
)
def hover(target: str, duration: float = 0.5) -> bool:
    return {"implemented": False, "description": "鼠标悬停"}


@feature(
    name="mouse_move",
    display_name="鼠标移动",
    description="【鼠标】将鼠标移动到绝对坐标位置。用于精确控制鼠标位置",
    category=F.ACTION,
    params=[
        P("x", "int", "目标 X 坐标"),
        P("y", "int", "目标 Y 坐标"),
        P("human_like", "boolean", "是否模拟人类移动轨迹", required=False, default=True),
    ],
    returns="bool - 是否成功",
    tags=["待完善"],
)
def mouse_move(x: int, y: int, human_like: bool = True) -> bool:
    return {"implemented": False, "description": "鼠标移动到坐标"}


@feature(
    name="triple_click",
    display_name="三击",
    description="【鼠标】在目标上执行三次点击。用于选中整段文本或触发特定应用功能",
    category=F.ACTION,
    params=[
        P("target", "str", "目标：文字 / 坐标 / 图像模板名", example="段落文本"),
    ],
    returns="bool - 是否成功",
    tags=["待完善"],
)
def triple_click(target: str) -> bool:
    return {"implemented": False, "description": "三击选中"}


@feature(
    name="select_text",
    display_name="选中文本",
    description="【鼠标】在目标位置执行双击选中单词或拖动选中范围。用于后续复制或操作",
    category=F.ACTION,
    params=[
        P("target", "str", "要选中的文字或其附近坐标", example="关键词"),
        P("extend_to_line", "boolean", "是否扩展到整行", required=False, default=False),
    ],
    returns="bool - 是否成功",
    tags=["待完善"],
)
def select_text(target: str, extend_to_line: bool = False) -> bool:
    return {"implemented": False, "description": "选中文本"}


@feature(
    name="middle_click",
    display_name="中键点击",
    description="【鼠标】在目标上执行鼠标中键点击。用于浏览器新标签页打开、画布平移等场景",
    category=F.ACTION,
    params=[
        P("target", "str", "目标：文字 / 坐标 / 图像模板名", example="链接文字"),
    ],
    returns="bool - 是否成功",
    tags=["待完善"],
)
def middle_click(target: str) -> bool:
    return {"implemented": False, "description": "中键点击"}
