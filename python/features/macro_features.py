"""
宏录制播放功能
录制 / 播放 / 管理宏 — 基于 pynput
"""
import json, os, time, threading
from datetime import datetime
from pathlib import Path

from features.registry import feature, P, TC, FeatureCategory as F

_MACRO_DIR = Path(__file__).resolve().parent.parent / "macros"
_MACRO_DIR.mkdir(exist_ok=True)

_recording = {"active": False, "events": [], "start": 0, "thread": None}


def _macro_path(name: str) -> Path:
    return _MACRO_DIR / f"{name}.json"


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
    tags=["macro", "recording"],
)
def macro_record(name: str, include_mouse: bool = True, include_keys: bool = True, duration: float = 30) -> dict:
    global _recording
    if _recording["active"]:
        return {"success": False, "error": "已有录制在进行中"}

    try:
        from pynput import mouse, keyboard
    except ImportError:
        return {"success": False, "error": "需要 pynput: pip install pynput"}

    _recording["active"] = True
    _recording["events"] = []
    _recording["start"] = time.time()

    def on_click(x, y, button, pressed):
        if not _recording["active"]:
            return False
        if include_mouse:
            _recording["events"].append({
                "type": "click", "time": time.time() - _recording["start"],
                "x": x, "y": y, "button": str(button), "pressed": pressed,
            })

    def on_move(x, y):
        if not _recording["active"]:
            return False
        if include_mouse:
            if not _recording["events"] or _recording["events"][-1].get("type") != "move":
                _recording["events"].append({
                    "type": "move", "time": time.time() - _recording["start"],
                    "x": x, "y": y,
                })

    def on_press(key):
        if not _recording["active"]:
            return False
        if include_keys:
            try:
                k = key.char
            except AttributeError:
                k = str(key)
            _recording["events"].append({
                "type": "key", "time": time.time() - _recording["start"],
                "key": k, "pressed": True,
            })

    def on_release(key):
        if not _recording["active"]:
            return False
        if include_keys:
            try:
                k = key.char
            except AttributeError:
                k = str(key)
            _recording["events"].append({
                "type": "key", "time": time.time() - _recording["start"],
                "key": k, "pressed": False,
            })

    m_listener = mouse.Listener(on_click=on_click, on_move=on_move)
    k_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    m_listener.start()
    k_listener.start()

    def _stop_after():
        time.sleep(duration)
        _recording["active"] = False
        m_listener.stop()
        k_listener.stop()

    threading.Thread(target=_stop_after, daemon=True).start()
    _recording["active"] = True

    # 等待录制完成
    while _recording["active"]:
        time.sleep(0.1)
    m_listener.join(timeout=2)
    k_listener.join(timeout=2)

    actual_duration = time.time() - _recording["start"]
    events = _recording["events"]
    _recording["active"] = False

    # 保存到文件
    data = {
        "name": name, "events": events,
        "duration": round(actual_duration, 1),
        "created": datetime.now().isoformat(),
        "include_mouse": include_mouse, "include_keys": include_keys,
    }
    with open(_macro_path(name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "success": True,
        "result": {"name": name, "events": len(events), "duration": round(actual_duration, 1)},
    }


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
    tags=["macro", "playback"],
)
def macro_playback(name: str, speed: float = 1.0, loop: int = 0) -> dict:
    path = _macro_path(name)
    if not path.exists():
        return {"success": False, "error": f"宏 '{name}' 不存在"}

    try:
        import pyautogui
    except ImportError:
        return {"success": False, "error": "需要 pyautogui: pip install pyautogui"}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    events = data.get("events", [])
    if not events:
        return {"success": True, "result": True}

    iterations = loop if loop > 0 else 1
    for _ in range(iterations):
        prev_time = 0
        for ev in events:
            delay = (ev["time"] - prev_time) / speed
            if delay > 0:
                time.sleep(delay)
            prev_time = ev["time"]

            if ev["type"] == "click" and ev["pressed"]:
                button = "left" if "left" in ev.get("button", "") else \
                         "right" if "right" in ev.get("button", "") else "middle"
                pyautogui.click(ev["x"], ev["y"], button=button)
            elif ev["type"] == "move":
                pyautogui.moveTo(ev["x"], ev["y"], duration=0.05)
            elif ev["type"] == "key" and ev["pressed"]:
                key = ev["key"]
                if key.startswith("Key."):
                    key = key.replace("Key.", "")
                    special_keys = {"enter": "enter", "tab": "tab", "space": "space",
                                    "backspace": "backspace", "esc": "escape",
                                    "shift": "shift", "ctrl": "ctrl", "alt": "alt"}
                    special_keys.get(key.lower(), key)
                try:
                    pyautogui.write(key, interval=0.01)
                except Exception:
                    pyautogui.press(key)

    return {"success": True, "result": True}


@feature(
    name="macro_list",
    display_name="列出宏",
    description="【宏】列出所有已录制的宏。用于查看和管理已有的宏",
    category=F.MACRO,
    params=[],
    returns="list[dict{name, events, duration, created}] - 宏列表",
    tags=["macro", "management"],
)
def macro_list() -> dict:
    macros = []
    for f in sorted(_MACRO_DIR.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            macros.append({
                "name": data.get("name", f.stem),
                "events": len(data.get("events", [])),
                "duration": data.get("duration", 0),
                "created": data.get("created", ""),
            })
        except Exception:
            macros.append({"name": f.stem, "error": "读取失败"})
    return {"success": True, "result": macros}
