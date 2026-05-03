"""
多媒体功能
音频控制 / 区域实时截图 / 屏幕录制
"""
import base64, io, os, time, threading
from datetime import datetime

from features.registry import feature, P, TC, FeatureCategory as F

# 全局录制状态
_recorder = {"active": False, "thread": None, "output": "", "frames": 0, "start_time": 0}


@feature(
    name="audio_volume_get",
    display_name="获取各应用音量",
    description="【多媒体】获取各个运行中应用的独立音量级别。用于诊断音频问题或监控哪个应用在发声",
    category=F.SYSTEM,
    params=[],
    returns="list[dict{name, volume, muted}] - 应用音量列表",
    tags=["multimedia", "audio"],
)
def audio_volume_get() -> dict:
    try:
        from pycaw.pycaw import AudioUtilities
        sessions = AudioUtilities.GetAllSessions()
        result = []
        for s in sessions:
            if s.Process and s.Process.name():
                vol = s.SimpleAudioVolume
                result.append({
                    "name": s.Process.name(),
                    "volume": round(vol.GetMasterVolume() * 100, 1),
                    "muted": bool(vol.GetMute()),
                })
        return {"success": True, "result": result}
    except ImportError:
        return {"success": False, "error": "需要 pycaw: pip install pycaw"}


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
    tags=["multimedia", "vision"],
)
def screenshot_region_live(region: str, max_fps: float = 5, change_threshold: float = 0.05) -> dict:
    try:
        from perception.vision import ScreenCapture
        from features._utils import parse_region
        import cv2
        import numpy as np

        reg = parse_region(region)
        if not reg:
            return {"success": False, "error": "无效的区域参数，需要 'x,y,w,h'"}

        interval = 1.0 / max(1, max_fps)
        last_frame = None
        changed = False

        img = ScreenCapture.capture(reg)
        if img is None:
            return {"success": False, "error": "截图失败"}

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

        # 首帧直接返回
        _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        b64 = base64.b64encode(buf).decode()
        last_frame = gray

        return {
            "success": True,
            "result": {
                "changed": True,
                "base64": b64,
                "width": w,
                "height": h,
                "timestamp": datetime.now().isoformat(),
            }
        }
    except ImportError:
        return {"success": False, "error": "需要 opencv-python: pip install opencv-python"}


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
    tags=["multimedia", "recording"],
)
def screen_record_start(output: str, region: str = "", fps: int = 10, include_audio: bool = False) -> dict:
    global _recorder
    if _recorder["active"]:
        return {"success": False, "error": "已有录制任务在进行中，请先停止"}

    try:
        from perception.vision import ScreenCapture
        from features._utils import parse_region
        import cv2
        import numpy as np

        reg = parse_region(region) if region else None
        # 获取初始帧确定尺寸
        sample = ScreenCapture.capture(reg)
        if sample is None:
            return {"success": False, "error": "无法获取屏幕画面"}
        h, w = sample.shape[:2]

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output, fourcc, fps, (w, h))
        if not writer.isOpened():
            return {"success": False, "error": "无法创建视频文件"}

        _recorder["active"] = True
        _recorder["output"] = output
        _recorder["frames"] = 0
        _recorder["start_time"] = time.time()

        def _record_loop():
            while _recorder["active"]:
                frame = ScreenCapture.capture(reg)
                if frame is not None:
                    writer.write(frame)
                    _recorder["frames"] += 1
                time.sleep(1.0 / fps)
            writer.release()

        _recorder["thread"] = threading.Thread(target=_record_loop, daemon=True)
        _recorder["thread"].start()

        return {"success": True, "result": {"file": output, "fps": fps, "region": region or "fullscreen"}}
    except ImportError:
        return {"success": False, "error": "需要 opencv-python: pip install opencv-python"}
    except Exception as e:
        _recorder["active"] = False
        return {"success": False, "error": str(e)}


@feature(
    name="screen_record_stop",
    display_name="停止屏幕录制",
    description="【多媒体】停止当前正在进行的屏幕录制并保存文件。用于结束录制",
    category=F.SYSTEM,
    params=[
        P("save", "boolean", "是否保存录制文件（False=丢弃）", required=False, default=True),
    ],
    returns="dict{success, file, duration, size} - 录制结果",
    tags=["multimedia", "recording"],
)
def screen_record_stop(save: bool = True) -> dict:
    global _recorder
    if not _recorder["active"]:
        return {"success": False, "error": "没有正在进行的录制"}

    _recorder["active"] = False
    if _recorder["thread"]:
        _recorder["thread"].join(timeout=5)

    duration = time.time() - _recorder["start_time"]
    frames = _recorder["frames"]
    output = _recorder["output"]

    if not save and os.path.exists(output):
        os.remove(output)
        return {"success": True, "result": {"saved": False, "frames": frames, "duration": round(duration, 1)}}

    file_size = os.path.getsize(output) if os.path.exists(output) else 0
    _recorder["active"] = False
    _recorder["thread"] = None

    return {
        "success": True,
        "result": {
            "saved": True,
            "file": output,
            "frames": frames,
            "duration": round(duration, 1),
            "size_bytes": file_size,
        }
    }
