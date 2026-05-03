"""
窗口操作功能
最小化 / 最大化 / 还原 / 调整大小 / 贴靠 / 关闭 — 基于 win32gui
"""
import time

from features.registry import feature, P, TC, FeatureCategory as F


def _find_hwnd(title: str):
    """按标题查找窗口句柄。留空返回前台窗口"""
    if not title:
        try:
            import win32gui
            return win32gui.GetForegroundWindow()
        except Exception:
            return None
    try:
        import win32gui
        def cb(hwnd, ctx):
            if title.lower() in win32gui.GetWindowText(hwnd).lower():
                ctx.append(hwnd)
        handles = []
        win32gui.EnumWindows(cb, handles)
        return handles[0] if handles else None
    except Exception:
        return None


def _show_window(title: str, cmd: int) -> bool:
    """通用：发送 ShowWindow 命令给窗口"""
    try:
        import win32gui
        import win32con
        hwnd = _find_hwnd(title)
        if not hwnd:
            return False
        win32gui.ShowWindow(hwnd, cmd)
        return True
    except ImportError:
        return False


@feature(
    name="window_minimize",
    display_name="最小化窗口",
    description="【窗口】最小化指定窗口到任务栏。用于临时隐藏窗口或清理桌面",
    category=F.SYSTEM,
    params=[
        P("title", "str", "窗口标题（留空则操作当前活动窗口）", required=False, default=""),
    ],
    returns="bool - 是否成功",
    tags=["window", "win32"],
)
def window_minimize(title: str = "") -> bool:
    try:
        import win32gui
        import win32con
        hwnd = _find_hwnd(title)
        if not hwnd:
            return False
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        return True
    except ImportError:
        return False


@feature(
    name="window_maximize",
    display_name="最大化窗口",
    description="【窗口】最大化指定窗口到全屏。用于获得更大工作区域",
    category=F.SYSTEM,
    params=[
        P("title", "str", "窗口标题（留空则操作当前活动窗口）", required=False, default=""),
    ],
    returns="bool - 是否成功",
    tags=["window", "win32"],
)
def window_maximize(title: str = "") -> bool:
    try:
        import win32gui
        import win32con
        hwnd = _find_hwnd(title)
        if not hwnd:
            return False
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        return True
    except ImportError:
        return False


@feature(
    name="window_restore",
    display_name="还原窗口",
    description="【窗口】将最大化/最小化的窗口还原到正常大小。用于恢复窗口位置",
    category=F.SYSTEM,
    params=[
        P("title", "str", "窗口标题（留空则操作当前活动窗口）", required=False, default=""),
    ],
    returns="bool - 是否成功",
    tags=["window", "win32"],
)
def window_restore(title: str = "") -> bool:
    try:
        import win32gui
        import win32con
        hwnd = _find_hwnd(title)
        if not hwnd:
            return False
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except ImportError:
        return False


@feature(
    name="window_resize",
    display_name="调整窗口大小",
    description="【窗口】将指定窗口调整为特定宽度和高度。用于精确控制窗口布局",
    category=F.SYSTEM,
    params=[
        P("width", "int", "目标宽度（像素）", example=1024),
        P("height", "int", "目标高度（像素）", example=768),
        P("title", "str", "窗口标题（留空则操作当前活动窗口）", required=False, default=""),
    ],
    returns="bool - 是否成功",
    tags=["window", "win32"],
)
def window_resize(width: int, height: int, title: str = "") -> bool:
    try:
        import win32gui
        import win32con
        hwnd = _find_hwnd(title)
        if not hwnd:
            return False
        # 获取当前位置，只改大小
        rect = win32gui.GetWindowRect(hwnd)
        x, y = rect[0], rect[1]
        # 应用新大小（需要先移除最大化限制）
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.05)
        win32gui.MoveWindow(hwnd, x, y, width, height, True)
        return True
    except ImportError:
        return False


@feature(
    name="window_snap",
    display_name="窗口贴靠",
    description="【窗口】将窗口贴靠到屏幕左/右/上/下半边。用于分屏多任务处理",
    category=F.SYSTEM,
    params=[
        P("position", "str", "贴靠位置: left|right|top|bottom|top_left|top_right|bottom_left|bottom_right", example="left"),
        P("title", "str", "窗口标题（留空则操作当前活动窗口）", required=False, default=""),
    ],
    returns="bool - 是否成功",
    tags=["window", "win32"],
)
def window_snap(position: str, title: str = "") -> bool:
    try:
        import win32gui
        hwnd = _find_hwnd(title)
        if not hwnd:
            return False
        # 获取屏幕工作区域
        import ctypes
        user32 = ctypes.windll.user32
        sw = user32.GetSystemMetrics(0)  # 屏幕宽度
        sh = user32.GetSystemMetrics(1)  # 屏幕高度
        # 任务栏占用估算
        taskbar = 40
        work_w, work_h = sw, sh - taskbar

        regions = {
            "left":          (0, 0, work_w // 2, work_h),
            "right":         (work_w // 2, 0, work_w, work_h),
            "top":           (0, 0, work_w, work_h // 2),
            "bottom":        (0, work_h // 2, work_w, work_h),
            "top_left":      (0, 0, work_w // 2, work_h // 2),
            "top_right":     (work_w // 2, 0, work_w, work_h // 2),
            "bottom_left":   (0, work_h // 2, work_w // 2, work_h),
            "bottom_right":  (work_w // 2, work_h // 2, work_w, work_h),
        }
        pos = position.lower().replace("-", "_")
        if pos not in regions:
            return False
        x, y, w, h = regions[pos]
        win32gui.MoveWindow(hwnd, x, y, w, h, True)
        return True
    except ImportError:
        return False


@feature(
    name="window_close",
    display_name="关闭窗口",
    description="【窗口】关闭指定窗口（发送关闭信号）。用于关闭不需要的窗口或对话框",
    category=F.SYSTEM,
    params=[
        P("title", "str", "窗口标题（留空则操作当前活动窗口）", required=False, default=""),
        P("force", "boolean", "是否强制关闭", required=False, default=False),
    ],
    returns="bool - 是否成功",
    tags=["window", "win32"],
)
def window_close(title: str = "", force: bool = False) -> bool:
    try:
        import win32gui
        import win32con
        hwnd = _find_hwnd(title)
        if not hwnd:
            return False
        if force:
            import ctypes
            ctypes.windll.user32.TerminateProcess(
                ctypes.windll.kernel32.GetWindowThreadProcessId(hwnd, 0), 0)
        else:
            win32gui.SendMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        return True
    except ImportError:
        return False
