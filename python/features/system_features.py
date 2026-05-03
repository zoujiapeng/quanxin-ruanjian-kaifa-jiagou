"""
系统功能注册
进程检测 / 窗口管理 / 剪贴板输入
"""
import time

from features.registry import feature, P, TC, FeatureCategory as F


@feature(
    name="detect_process",
    display_name="检测进程",
    description="【系统·进程】检查指定进程是否在运行中。使用场景：确认目标软件是否已启动、等待进程启动后再操作。组合：先 detect_process 检查 → 未运行则先启动 → 再用 focus_window 切换到该窗口 → 执行 click_target/type_text。LOOP 模式：LOOP → detect_process → IF found → 继续后续操作 → END",
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
    description="【系统·进程详情】查找所有匹配的进程，返回详细信息（PID、CPU、内存）。使用场景：获取进程 PID 用于监控、检查是否有残留进程、分析资源占用。组合：find_processes 查 PID → 用于 Debug 场景。比 detect_process 更详细，但更重",
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
    description="【系统·窗口激活】将指定标题的窗口带到前台。使用场景：在多任务中切换到目标应用窗口、操作前确保目标窗口在前台。组合：list_windows 查看所有窗口 → focus_window 切换到目标 → click_target/type_text 操作。注意：Windows 限制跨进程置前，有时第一次可能失败，建议重试",
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
    description="【系统·窗口列表】列出当前所有可见窗口的标题。使用场景：了解当前打开的窗口、查找目标窗口的精确标题、监控窗口变化。组合：list_windows 查看 → 用返回的标题传给 focus_window 激活 → 操作完成后再次 list_windows 验证新窗口",
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
    description="【系统·当前窗口】获取当前活动窗口的信息（标题、位置、大小）。使用场景：在做操作前确认当前窗口上下文、记录窗口位置用于后续操作、监控窗口变化。组合：get_active_window 确认 → focus_window 确保正确窗口 → 执行操作。可用于 LOOP 中检测窗口变化：LOOP → get_active_window → IF title改变 → 适应新窗口",
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
