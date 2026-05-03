"""
系统功能注册
进程检测 / 窗口管理 / 剪贴板输入
"""
import time

from features.registry import feature, P, TC, FeatureCategory as F


@feature(
    name="detect_process",
    display_name="检测进程",
    description="【系统·进程】检查指定进程是否在运行中。用于确认目标软件已启动或等待进程退出",
    category=F.SYSTEM,
    params=[
        P("name", "str", "进程名称，如 notepad.exe、chrome.exe", example="notepad.exe"),
        P("exact", "boolean", "是否精确匹配", required=False, default=False),
    ],
    returns="bool - 进程是否存在",
    test_cases=[
        TC("python", {"name": "python"}, "success",
           validator=lambda r: r.get("success") is True, skip_in_ci=False),
    ],
)
def detect_process(name: str, exact: bool = False) -> bool:
    try:
        from system.process import ProcessDetector
        return ProcessDetector().is_running(name, exact=exact)
    except ImportError:
        return False


@feature(
    name="find_processes",
    display_name="查找进程",
    description="【系统·进程详情】查找所有匹配的进程，返回 PID、CPU、内存等详细信息。比 detect_process 更详细，用于监控和诊断",
    category=F.SYSTEM,
    params=[
        P("name", "str", "进程名称", example="python"),
    ],
    returns="list[dict{pid, name, cpu, memory}]",
)
def find_processes(name: str) -> list:
    try:
        from system.process import ProcessDetector
        return ProcessDetector().find_processes(name)
    except ImportError:
        return []


@feature(
    name="focus_window",
    display_name="激活窗口",
    description="【系统·窗口激活】将指定标题的窗口带到前台。操作前确保目标窗口在前台。注意 Windows 限制跨进程置前，可能需重试",
    category=F.SYSTEM,
    params=[
        P("title", "str", "窗口标题（支持模糊匹配）", example="记事本"),
        P("exact", "boolean", "是否精确匹配", required=False, default=False),
    ],
    returns="bool - 是否成功",
    examples=["focus_window title=记事本"],
)
def focus_window(title: str, exact: bool = False) -> bool:
    try:
        from system.window import WindowManager
        return WindowManager().focus_window(title, exact=exact)
    except ImportError:
        return False


@feature(
    name="list_windows",
    display_name="列出窗口",
    description="【系统·窗口列表】列出当前所有可见窗口的标题。用于查找目标窗口标题或监控窗口变化",
    category=F.SYSTEM,
    params=[],
    returns="list[str] - 窗口标题列表",
)
def list_windows() -> list:
    try:
        from system.window import WindowManager
        return WindowManager().get_all_window_titles()
    except ImportError:
        return []


@feature(
    name="get_active_window",
    display_name="当前窗口信息",
    description="【系统·当前窗口】获取当前活动窗口的信息（标题、位置、大小）。用于确认当前操作上下文或监控窗口变化",
    category=F.SYSTEM,
    params=[],
    returns="dict{title, left, top, width, height}",
)
def get_active_window() -> dict:
    try:
        from system.window import WindowManager
        result = WindowManager().get_active_window()
        return result or {"error": "无法获取窗口信息"}
    except ImportError:
        return {"error": "窗口管理模块不可用"}
