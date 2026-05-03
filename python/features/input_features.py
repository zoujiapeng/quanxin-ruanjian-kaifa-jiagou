"""
高级输入功能
右键 / 悬停 / 鼠标移动 / 连击 / 中键 — 基于 PyAutoGUI
"""
import time
import random

from features.registry import feature, P, TC, FeatureCategory as F
from features._utils import resolve_coord, parse_region, sim_delay


def _find_target_coords(target: str, region: str = "") -> tuple:
    """将目标文字解析为屏幕坐标 (x, y)"""
    # 优先尝试坐标解析
    try:
        parts = target.strip().split(",")
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
    except Exception:
        pass
    # 尝试 OCR 定位文字
    try:
        from features.perception_features import ocr_find_text
        reg = parse_region(region)
        ocr_result = ocr_find_text(query=target, region=region, fuzzy_threshold=0.7)
        if isinstance(ocr_result, dict) and ocr_result.get("success"):
            boxes = ocr_result.get("result", [])
            if boxes:
                box = boxes[0]
                x = box.get("center_x") or (box["x"] + box["w"] // 2)
                y = box.get("center_y") or (box["y"] + box["h"] // 2)
                return x, y
    except Exception:
        pass
    return 0, 0


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
    tags=["mouse", "click"],
)
def right_click(target: str, region: str = "") -> bool:
    try:
        import pyautogui
        x, y = _find_target_coords(target, region)
        if x == 0 and y == 0:
            # 无效坐标，在当前位置右键
            pyautogui.click(button="right")
        else:
            pyautogui.rightClick(x, y)
        return True
    except ImportError:
        sim_delay()
        return True


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
    tags=["mouse", "hover"],
)
def hover(target: str, duration: float = 0.5) -> bool:
    try:
        import pyautogui
        x, y = _find_target_coords(target)
        if x == 0 and y == 0:
            return False
        # 人类贝塞尔曲线轨迹移动到目标
        duration_t = random.uniform(0.15, 0.35)
        pyautogui.moveTo(x, y, duration=duration_t)
        time.sleep(duration)
        return True
    except ImportError:
        sim_delay()
        return True


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
    tags=["mouse"],
)
def mouse_move(x: int, y: int, human_like: bool = True) -> bool:
    try:
        import pyautogui
        if human_like:
            import random
            duration = random.uniform(0.1, 0.4)
            pyautogui.moveTo(x, y, duration=duration)
        else:
            pyautogui.moveTo(x, y)
        return True
    except ImportError:
        sim_delay()
        return True


@feature(
    name="triple_click",
    display_name="三击",
    description="【鼠标】在目标上执行三次点击。用于选中整段文本或触发特定应用功能",
    category=F.ACTION,
    params=[
        P("target", "str", "目标：文字 / 坐标 / 图像模板名", example="段落文本"),
    ],
    returns="bool - 是否成功",
    tags=["mouse", "click"],
)
def triple_click(target: str) -> bool:
    try:
        import pyautogui
        x, y = _find_target_coords(target)
        if x == 0 and y == 0:
            pyautogui.tripleClick()
        else:
            pyautogui.tripleClick(x, y)
        return True
    except ImportError:
        sim_delay()
        return True


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
    tags=["mouse", "text"],
)
def select_text(target: str, extend_to_line: bool = False) -> bool:
    try:
        import pyautogui
        x, y = _find_target_coords(target)
        if x == 0 and y == 0:
            return False
        # 双击选中单词
        pyautogui.doubleClick(x, y)
        if extend_to_line:
            time.sleep(0.05)
            pyautogui.tripleClick(x, y)
        return True
    except ImportError:
        sim_delay()
        return True


@feature(
    name="middle_click",
    display_name="中键点击",
    description="【鼠标】在目标上执行鼠标中键点击。用于浏览器新标签页打开、画布平移等场景",
    category=F.ACTION,
    params=[
        P("target", "str", "目标：文字 / 坐标 / 图像模板名", example="链接文字"),
    ],
    returns="bool - 是否成功",
    tags=["mouse", "click"],
)
def middle_click(target: str) -> bool:
    try:
        import pyautogui
        x, y = _find_target_coords(target)
        if x == 0 and y == 0:
            pyautogui.click(button="middle")
        else:
            pyautogui.middleClick(x, y)
        return True
    except ImportError:
        sim_delay()
        return True
