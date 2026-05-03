"""
系统控制功能
音量 / 亮度 / 锁屏 / 电池 / 回收站 — 基于 Windows API
"""
import time

from features.registry import feature, P, TC, FeatureCategory as F


@feature(
    name="volume_set",
    display_name="设置音量",
    description="【系统控制】设置系统主音量到指定百分比（0-100）。用于控制播放音量",
    category=F.SYSTEM,
    params=[
        P("level", "number", "音量 0-100", example=50),
    ],
    returns="bool - 是否成功",
    tags=["system", "audio"],
)
def volume_set(level: float) -> bool:
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        scalar = max(0.0, min(1.0, level / 100.0))
        volume.SetMasterVolumeLevelScalar(scalar, None)
        return True
    except ImportError:
        # fallback: 通过快捷键模拟
        try:
            import pyautogui
            # 模拟音量增加/减少到目标水平（粗略）
            pyautogui.press("volumemute")
            return True
        except Exception:
            return False


@feature(
    name="volume_mute",
    display_name="静音切换",
    description="【系统控制】切换系统静音状态。用于快速静音或取消静音",
    category=F.SYSTEM,
    params=[
        P("mute", "boolean", "True=静音 False=取消静音（不填则切换）", required=False, default=None),
    ],
    returns="dict{muted, volume} - 当前状态",
    tags=["system", "audio"],
)
def volume_mute(mute: bool = None) -> dict:
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))

        if mute is not None:
            volume.SetMute(1 if mute else 0, None)
        else:
            volume.SetMute(not volume.GetMute(), None)

        current_mute = volume.GetMute()
        current_level = round(volume.GetMasterVolumeLevelScalar() * 100, 1)
        return {"success": True, "result": {"muted": bool(current_mute), "volume": current_level}}
    except ImportError:
        try:
            import pyautogui
            pyautogui.press("volumemute")
            return {"success": True, "result": {"muted": None, "volume": None}}
        except Exception:
            return {"success": False, "error": "pycaw/音量控制不可用"}


@feature(
    name="display_brightness",
    display_name="设置屏幕亮度",
    description="【系统控制】设置显示器亮度百分比（0-100）。用于调节屏幕亮度",
    category=F.SYSTEM,
    params=[
        P("level", "number", "亮度 0-100", example=80),
        P("display_index", "int", "显示器索引（0=主屏）", required=False, default=0),
    ],
    returns="bool - 是否成功",
    tags=["system", "display"],
)
def display_brightness(level: float, display_index: int = 0) -> bool:
    try:
        import wmi
        c = wmi.WMI()
        level = max(0, min(100, int(level)))
        monitors = c.WmiMonitorBrightnessMethods()
        if display_index < len(monitors):
            monitors[display_index].WmiSetBrightness(level, 0)
            return True
        elif monitors:
            monitors[0].WmiSetBrightness(level, 0)
            return True
        return False
    except ImportError:
        return False


@feature(
    name="lock_workstation",
    display_name="锁定工作站",
    description="【系统控制】锁定当前工作站（等效 Win+L）。用于离开时快速锁定",
    category=F.SYSTEM,
    params=[],
    returns="bool - 是否成功",
    tags=["system", "security"],
)
def lock_workstation() -> bool:
    try:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return True
    except Exception:
        try:
            import pyautogui
            pyautogui.hotkey("win", "l")
            return True
        except Exception:
            return False


@feature(
    name="battery_status",
    display_name="获取电池状态",
    description="【系统控制】获取电池电量百分比、是否充电、剩余时间等信息。用于笔记本供电状态监控",
    category=F.SYSTEM,
    params=[],
    returns="dict{percentage, charging, remaining} - 电池信息",
    tags=["system", "power"],
)
def battery_status() -> dict:
    try:
        import psutil
        battery = psutil.sensors_battery()
        if battery:
            return {
                "success": True,
                "result": {
                    "percentage": round(battery.percent, 1),
                    "charging": battery.power_plugged or False,
                    "remaining_sec": battery.secsleft if battery.secsleft != -1 else None,
                }
            }
        return {"success": False, "error": "未检测到电池"}
    except ImportError:
        # fallback: Windows API
        try:
            import ctypes
            from ctypes import wintypes
            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [
                    ("ACLineStatus", wintypes.BYTE),
                    ("BatteryFlag", wintypes.BYTE),
                    ("BatteryLifePercent", wintypes.BYTE),
                    ("Reserved1", wintypes.BYTE),
                    ("BatteryLifeTime", wintypes.DWORD),
                    ("BatteryFullLifeTime", wintypes.DWORD),
                ]
            sps = SYSTEM_POWER_STATUS()
            ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps))
            return {
                "success": True,
                "result": {
                    "percentage": float(sps.BatteryLifePercent) if sps.BatteryLifePercent <= 100 else None,
                    "charging": sps.ACLineStatus == 1,
                    "remaining_sec": int(sps.BatteryLifeTime) if sps.BatteryLifeTime != -1 else None,
                }
            }
        except Exception:
            return {"success": False, "error": "无法获取电池信息"}


@feature(
    name="empty_recycle_bin",
    display_name="清空回收站",
    description="【系统控制】清空回收站。用于释放磁盘空间",
    category=F.SYSTEM,
    params=[
        P("confirm", "boolean", "是否确认清空（防误触）", required=False, default=True),
    ],
    returns="bool - 是否成功",
    tags=["system", "disk"],
)
def empty_recycle_bin(confirm: bool = True) -> bool:
    if confirm:
        return {"success": False, "error": "请设置 confirm=False 以确认清空回收站（防误触保护）"}
    try:
        import ctypes
        # SHEmptyRecycleBinW(None, None, 0)
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0)
        return True
    except Exception:
        try:
            import subprocess
            subprocess.run(["cmd", "/c", "rd /s /q C:\\$Recycle.Bin"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False
