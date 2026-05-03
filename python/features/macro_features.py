"""
宏录制播放功能注册（待完善）
录制 / 播放 / 管理宏
"""
from features.registry import feature, P, TC, FeatureCategory as F


@feature(
    name="macro_record",
    display_name="录制宏",
    description="【宏】录制鼠标和键盘操作序列。用于记录重复性操作以便后续回放",
    category=F.MACRO,
    params=[
        P("name", "str", "宏名称", example="登录流程"),
        P("include_mouse", "boolean", "是否录制鼠标移动", required=False, default=True),
        P("include_keys", "boolean", "是否录制键盘输入", required=False, default=True),
        P("duration", "number", "最大录制秒数", required=False, default=30),
    ],
    returns="dict{name, events, duration} - 录制结果",
    tags=["待完善"],
)
def macro_record(name: str, include_mouse: bool = True, include_keys: bool = True, duration: float = 30) -> dict:
    return {"implemented": False, "description": "录制宏"}


@feature(
    name="macro_playback",
    display_name="播放宏",
    description="【宏】播放已录制的宏操作序列。用于自动重现录制的操作流程",
    category=F.MACRO,
    params=[
        P("name", "str", "宏名称", example="登录流程"),
        P("speed", "number", "播放速度倍率", required=False, default=1.0),
        P("loop", "int", "循环次数（0=不循环）", required=False, default=0),
    ],
    returns="bool - 是否播放成功",
    tags=["待完善"],
)
def macro_playback(name: str, speed: float = 1.0, loop: int = 0) -> bool:
    return {"implemented": False, "description": "播放宏"}


@feature(
    name="macro_list",
    display_name="列出宏",
    description="【宏】列出所有已录制的宏。用于查看和管理已有的宏",
    category=F.MACRO,
    params=[],
    returns="list[dict{name, events, duration, created}] - 宏列表",
    tags=["待完善"],
)
def macro_list() -> list:
    return {"implemented": False, "description": "列出宏"}
