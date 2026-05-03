"""
动作类功能注册
CLICK / TYPE / SCROLL / DRAG / HOTKEY
"""
import time

from features.registry import feature, P, TC, FeatureCategory as F
from features._utils import parse_region, resolve_coord, sim_delay


@feature(
    name="click_target",
    display_name="点击目标",
    description="【核心操作】语义点击：自动融合 OCR 文字 + 图像模板 + 坐标三种策略定位目标并点击。适用于任何需要点击屏幕元素的场景",
    category=F.ACTION,
    params=[
        P("target", "str", "目标：文字内容 / 图像模板名 / 'x,y' 坐标", example="确认按钮"),
        P("region", "str", "限定搜索区域 'x,y,w,h'（可选）", required=False, default=""),
        P("timeout", "number", "超时秒数", required=False, default=10),
        P("human_like", "boolean", "是否模拟人类行为", required=False, default=True),
        P("double", "boolean", "是否双击", required=False, default=False),
    ],
    returns="bool - 点击是否成功",
    dsl_keyword="CLICK",
    dsl_template="CLICK {target}",
    examples=["CLICK 开始游戏", "CLICK 确认"],
    test_cases=[
        TC("no_target", {"target": ""}, "success",
           validator=lambda r: r.get("success") is True, skip_in_ci=True),
    ],
)
def click_target(target: str, region: str = "", timeout: float = 10,
                 human_like: bool = True, double: bool = False) -> bool:
    try:
        from interaction.actions import ActionHandler
        handler = ActionHandler()
        parsed = parse_region(region)
        return handler.clicker.click(target, region=parsed, timeout=timeout, human=human_like)
    except ImportError:
        sim_delay()
        return True


@feature(
    name="type_text",
    display_name="输入文字",
    description="【键盘输入】模拟键盘输入文字，支持人类速度模拟（随机按键间隔）。适用于填写表单、输入搜索关键词。中文文本建议用 type_clipboard 替代（绕过输入法）",
    category=F.ACTION,
    params=[
        P("text", "str", "要输入的文字", example="Hello World"),
        P("clear_first", "boolean", "输入前先清空", required=False, default=False),
        P("interval", "number", "按键间隔秒数（0=随机人类速度）", required=False, default=0),
    ],
    returns="bool - 是否成功",
    dsl_keyword="TYPE",
    dsl_template="TYPE {text}",
    examples=["TYPE 搜索关键词", "TYPE 用户名"],
    test_cases=[
        TC("basic_type", {"text": "test"}, "bool_true", skip_in_ci=True),
    ],
)
def type_text(text: str, clear_first: bool = False, interval: float = 0) -> bool:
    try:
        from interaction.actions import HumanKeyboard
        import pyautogui
        if clear_first:
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.05)
        HumanKeyboard.type_text(text, interval=interval if interval > 0 else None)
        return True
    except ImportError:
        sim_delay()
        return True


@feature(
    name="scroll",
    display_name="滚动页面",
    description="【滚轮】在指定位置或区域滚动鼠标滚轮，支持方向（上/下/左/右）和滚动量。适用于翻页、滚动到页面特定位置",
    category=F.ACTION,
    params=[
        P("direction", "str", "方向: up | down | left | right", example="down"),
        P("amount", "number", "滚动量（单位：格）", required=False, default=3),
        P("x", "number", "X坐标（不填则当前位置）", required=False, default=-1),
        P("y", "number", "Y坐标（不填则当前位置）", required=False, default=-1),
    ],
    returns="bool - 是否成功",
    dsl_keyword="SCROLL",
    dsl_template="SCROLL {direction}",
    examples=["SCROLL down", "SCROLL up"],
    test_cases=[
        TC("scroll_down", {"direction": "down"}, "bool_true", skip_in_ci=True),
    ],
)
def scroll(direction: str, amount: int = 3, x: int = -1, y: int = -1) -> bool:
    try:
        import pyautogui
        clicks = amount if direction in ("down", "right") else -amount
        kwargs = {}
        if x >= 0 and y >= 0:
            kwargs = {"x": x, "y": y}
        pyautogui.scroll(clicks, **kwargs)
        return True
    except ImportError:
        return True


@feature(
    name="drag",
    display_name="拖拽",
    description="【拖拽】从一个位置拖拽到另一个位置，支持文字/坐标定位。适用于拖拽文件、滑动条、调整窗口布局",
    category=F.ACTION,
    params=[
        P("from_target", "str", "起始目标（文字或坐标）", example="文件图标"),
        P("to_target", "str", "目标位置（文字或坐标）", example="目标文件夹"),
        P("duration", "number", "拖动耗时秒数", required=False, default=0.5),
    ],
    returns="bool - 是否成功",
    dsl_keyword="DRAG",
    dsl_template="DRAG {from_target} TO {to_target}",
    examples=["DRAG 文件图标 TO 目标文件夹"],
)
def drag(from_target: str, to_target: str, duration: float = 0.5) -> bool:
    try:
        from interaction.actions import HumanMouse
        x1, y1 = resolve_coord(from_target)
        x2, y2 = resolve_coord(to_target)
        HumanMouse.drag(x1, y1, x2, y2, duration=duration)
        return True
    except Exception:
        return False


@feature(
    name="hotkey",
    display_name="快捷键",
    description="【快捷键】按下快捷键组合，如 ctrl+c、alt+F4。适用于系统级操作、应用内快捷指令。组合键用 + 连接",
    category=F.ACTION,
    params=[
        P("keys", "str", "快捷键，用+连接，如 ctrl+c", example="ctrl+c"),
    ],
    returns="bool - 是否成功",
    dsl_keyword="HOTKEY",
    dsl_template="HOTKEY {keys}",
    examples=["HOTKEY ctrl+c", "HOTKEY alt+F4"],
    test_cases=[
        TC("ctrl_c", {"keys": "ctrl+c"}, "bool_true", skip_in_ci=True),
    ],
)
def hotkey(keys: str) -> bool:
    try:
        import pyautogui
        key_list = [k.strip() for k in keys.split("+")]
        pyautogui.hotkey(*key_list)
        return True
    except ImportError:
        return True


@feature(
    name="type_clipboard",
    display_name="剪贴板输入",
    description="【推荐中文输入】通过剪贴板粘贴文字，绕过输入法直接输入中文/特殊字符，保留原剪贴板内容。推荐所有东亚语言输入使用此工具而非 type_text",
    category=F.ACTION,
    params=[
        P("text", "str", "要输入的文字", example="你好世界"),
    ],
    returns="bool - 是否成功",
    dsl_keyword="TYPE_CLIP",
    dsl_template="TYPE_CLIP {text}",
    examples=["TYPE_CLIP 你好世界"],
    test_cases=[
        TC("basic", {"text": "test"}, "bool_true", skip_in_ci=True),
    ],
)
def type_clipboard(text: str) -> bool:
    try:
        import pyperclip
        import pyautogui
        import time
        # 保存原剪贴板
        old = pyperclip.paste()
        pyperclip.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)
        # 恢复
        pyperclip.copy(old)
        return True
    except ImportError:
        try:
            import pyautogui
            pyautogui.write(text, interval=0.05)
            return True
        except ImportError:
            return False
