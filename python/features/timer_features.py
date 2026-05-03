"""
定时条件功能注册（待完善）
等待文件 / 进程 / 网络 / 时间 / 倒计时
"""
from features.registry import feature, P, TC, FeatureCategory as F


@feature(
    name="timer_wait_file",
    display_name="等待文件",
    description="【定时条件】阻塞等待指定文件创建或出现。用于等待下载完成、导出完成等文件生成场景",
    category=F.CONTROL,
    params=[
        P("path", "str", "文件路径", example="C:\\下载\\report.pdf"),
        P("timeout", "number", "超时秒数", required=False, default=60),
        P("wait_delete", "boolean", "是否等待文件删除而非创建", required=False, default=False),
    ],
    returns="bool - 是否在规定时间内检测到",
    tags=["待完善"],
)
def timer_wait_file(path: str, timeout: float = 60, wait_delete: bool = False) -> bool:
    return {"implemented": False, "description": "等待文件出现或消失"}


@feature(
    name="timer_wait_process",
    display_name="等待进程",
    description="【定时条件】阻塞等待指定进程启动或退出。用于等待软件打开或关闭后再执行后续操作",
    category=F.CONTROL,
    params=[
        P("name", "str", "进程名称", example="notepad.exe"),
        P("timeout", "number", "超时秒数", required=False, default=60),
        P("wait_exit", "boolean", "是否等待进程退出而非启动", required=False, default=False),
    ],
    returns="bool - 是否在规定时间内检测到",
    tags=["待完善"],
)
def timer_wait_process(name: str, timeout: float = 60, wait_exit: bool = False) -> bool:
    return {"implemented": False, "description": "等待进程启动或退出"}


@feature(
    name="timer_wait_network",
    display_name="等待网络连接",
    description="【定时条件】阻塞等待网络连接恢复或断开。用于网络相关操作前确保连接状态",
    category=F.CONTROL,
    params=[
        P("timeout", "number", "超时秒数", required=False, default=30),
        P("wait_disconnect", "boolean", "是否等待断开而非连接", required=False, default=False),
    ],
    returns="bool - 是否在规定时间内达到目标状态",
    tags=["待完善"],
)
def timer_wait_network(timeout: float = 30, wait_disconnect: bool = False) -> bool:
    return {"implemented": False, "description": "等待网络连接或断开"}


@feature(
    name="timer_wait_time",
    display_name="等待到指定时间",
    description="【定时条件】阻塞等待直到系统时间到达指定时刻。用于定时任务、预约操作",
    category=F.CONTROL,
    params=[
        P("target", "str", "目标时间 HH:MM 或 HH:MM:SS 格式", example="14:30"),
    ],
    returns="bool - 是否到达指定时间",
    tags=["待完善"],
)
def timer_wait_time(target: str) -> bool:
    return {"implemented": False, "description": "等待到指定时间"}


@feature(
    name="timer_countdown",
    display_name="倒计时",
    description="【定时条件】阻塞等待指定的秒数。等效于 sleep，但支持中途取消检查",
    category=F.CONTROL,
    params=[
        P("seconds", "number", "等待秒数", example=5),
    ],
    returns="bool - 是否完整等待完毕（False 表示被取消）",
    tags=["待完善"],
)
def timer_countdown(seconds: float) -> bool:
    return {"implemented": False, "description": "倒计时等待"}
