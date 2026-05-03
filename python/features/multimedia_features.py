"""
多媒体功能注册（待完善）
音频控制 / 区域实时截图 / 屏幕录制
"""
from features.registry import feature, P, TC, FeatureCategory as F


@feature(
    name="audio_volume_get",
    display_name="获取各应用音量",
    description="【多媒体】获取各个运行中应用的独立音量级别。用于诊断音频问题或监控哪个应用在发声",
    category=F.SYSTEM,
    params=[],
    returns="list[dict{name, volume, muted}] - 应用音量列表",
    tags=["待完善"],
)
def audio_volume_get() -> list:
    return {"implemented": False, "description": "获取各应用音量"}


@feature(
    name="screenshot_region_live",
    display_name="区域实时截图",
    description="【多媒体】持续监控指定区域画面变化并返回最新截图（FPS 限制）。用于监控动态区域变化",
    category=F.PERCEPTION,
    params=[
        P("region", "str", "监控区域 'x,y,w,h'"),
        P("max_fps", "number", "最大帧率", required=False, default=5),
        P("change_threshold", "number", "变化检测阈值 0-1", required=False, default=0.05),
    ],
    returns="dict{changed, base64, timestamp} - 截图结果",
    tags=["待完善"],
)
def screenshot_region_live(region: str, max_fps: float = 5, change_threshold: float = 0.05) -> dict:
    return {"implemented": False, "description": "区域实时截图监控"}


@feature(
    name="screen_record_start",
    display_name="开始屏幕录制",
    description="【多媒体】开始录制屏幕到视频文件。用于录制操作过程",
    category=F.SYSTEM,
    params=[
        P("output", "str", "输出文件路径", example="C:\\录制\\demo.mp4"),
        P("region", "str", "录制区域（可选，默认全屏）", required=False, default=""),
        P("fps", "int", "帧率", required=False, default=10),
        P("include_audio", "boolean", "是否录制系统音频", required=False, default=False),
    ],
    returns="dict{success, file, pid} - 录制信息",
    tags=["待完善"],
)
def screen_record_start(output: str, region: str = "", fps: int = 10, include_audio: bool = False) -> dict:
    return {"implemented": False, "description": "开始屏幕录制"}


@feature(
    name="screen_record_stop",
    display_name="停止屏幕录制",
    description="【多媒体】停止当前正在进行的屏幕录制并保存文件。用于结束录制",
    category=F.SYSTEM,
    params=[
        P("save", "boolean", "是否保存录制文件（False=丢弃）", required=False, default=True),
    ],
    returns="dict{success, file, duration, size} - 录制结果",
    tags=["待完善"],
)
def screen_record_stop(save: bool = True) -> dict:
    return {"implemented": False, "description": "停止屏幕录制"}
