"""
交互层: 鼠标/键盘控制 + 人类行为模拟
- clickTarget: 语义点击（OCR + 图像 + 位置融合）
- waitUntil: 统一等待接口
- autoPopup: 自动弹窗处理
- humanAction: 模拟人类行为（随机延迟 + 曲线移动）
"""

from __future__ import annotations
import time
import math
import random
from typing import Optional, Tuple, Callable, Any, List

import pyautogui
import numpy as np

from perception.vision import ScreenCapture, TemplateMatcher, ChangeDetector, ColorDetector, BBox, Point
from perception.ocr import OCREngine

# 禁用 pyautogui 故障保险（生产中可调整）
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.0


# ── 工具函数 ──────────────────────────────────────────────────────
def _bezier_curve(
    p0: Point, p1: Point, p2: Point, num_points: int = 20
) -> List[Point]:
    """二次贝塞尔曲线插值"""
    points = []
    for i in range(num_points + 1):
        t = i / num_points
        x = int((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0])
        y = int((1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1])
        points.append((x, y))
    return points


class HumanMouse:
    """模拟人类鼠标行为"""

    @staticmethod
    def move_to(x: int, y: int, duration: Optional[float] = None):
        """贝塞尔曲线移动"""
        cx, cy = pyautogui.position()
        if duration is None:
            dist = math.hypot(x - cx, y - cy)
            duration = random.uniform(0.3, 0.8) * (dist / 1000 + 0.3)

        # 控制点随机偏移
        cp_x = cx + (x - cx) // 2 + random.randint(-100, 100)
        cp_y = cy + (y - cy) // 2 + random.randint(-100, 100)
        points = _bezier_curve((cx, cy), (cp_x, cp_y), (x, y), num_points=30)

        step_time = duration / len(points)
        for px, py in points:
            pyautogui.moveTo(px, py)
            time.sleep(step_time + random.uniform(-0.005, 0.005))

    @staticmethod
    def click(x: int, y: int, button: str = "left", jitter: int = 2):
        """模拟人类点击：轻微抖动 + 随机延迟"""
        jx = x + random.randint(-jitter, jitter)
        jy = y + random.randint(-jitter, jitter)
        HumanMouse.move_to(jx, jy)
        time.sleep(random.uniform(0.05, 0.15))
        pyautogui.mouseDown(button=button)
        time.sleep(random.uniform(0.05, 0.12))
        pyautogui.mouseUp(button=button)

    @staticmethod
    def double_click(x: int, y: int):
        HumanMouse.click(x, y)
        time.sleep(random.uniform(0.08, 0.15))
        HumanMouse.click(x, y)

    @staticmethod
    def right_click(x: int, y: int):
        HumanMouse.click(x, y, button="right")

    @staticmethod
    def drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.5):
        HumanMouse.move_to(x1, y1)
        pyautogui.mouseDown()
        time.sleep(0.1)
        HumanMouse.move_to(x2, y2, duration=duration)
        time.sleep(0.05)
        pyautogui.mouseUp()


class HumanKeyboard:
    """模拟人类键盘行为"""

    @staticmethod
    def type_text(text: str, interval: Optional[float] = None):
        for ch in text:
            if interval is None:
                delay = random.uniform(0.05, 0.15)
            else:
                delay = interval
            pyautogui.typewrite(ch, interval=0)
            time.sleep(delay)

    @staticmethod
    def press(key: str):
        pyautogui.press(key)
        time.sleep(random.uniform(0.03, 0.08))

    @staticmethod
    def hotkey(*keys: str):
        pyautogui.hotkey(*keys)
        time.sleep(random.uniform(0.05, 0.1))


class ClickTarget:
    """
    语义点击: OCR + 图像 + 位置融合策略
    fallback: OCR失败 → 图像匹配 → 坐标点击
    """

    def __init__(self, ocr: OCREngine, matcher: TemplateMatcher):
        self._ocr = ocr
        self._matcher = matcher

    def click(
        self,
        target: str,
        region: Optional[BBox] = None,
        timeout: float = 10.0,
        human: bool = True,
    ) -> bool:
        """
        尝试点击目标:
        1. 尝试 OCR 文字匹配
        2. 尝试图像模板匹配
        3. 尝试坐标表达式 "x,y"
        """
        end = time.time() + timeout
        while time.time() < end:
            pt = self._find_target(target, region)
            if pt:
                if human:
                    HumanMouse.click(pt[0], pt[1])
                else:
                    pyautogui.click(pt[0], pt[1])
                return True
            time.sleep(0.3)
        return False

    def _find_target(self, target: str, region: Optional[BBox]) -> Optional[Point]:
        # 策略1: 坐标表达式
        coord_match = __import__("re").match(r"^(\d+)\s*,\s*(\d+)$", target.strip())
        if coord_match:
            return int(coord_match.group(1)), int(coord_match.group(2))

        # 策略2: OCR 文字查找
        result = self._ocr.find_text(target, region=region)
        if result:
            return result.center

        # 策略3: 图像模板匹配
        match = self._matcher.find(target, region=region)
        if match:
            return match[0]

        return None


class WaitCondition:
    """统一等待接口"""

    def __init__(self, ocr: OCREngine, matcher: TemplateMatcher, detector: ChangeDetector):
        self._ocr = ocr
        self._matcher = matcher
        self._detector = detector

    def wait(
        self,
        condition: str,
        timeout: float = 30.0,
        interval: float = 0.5,
        region: Optional[BBox] = None,
    ) -> bool:
        """
        条件格式:
          "文字:XXX"    → 等待文字出现
          "图像:XXX"    → 等待图像出现
          "稳定"        → 等待画面稳定
          "变化"        → 等待画面变化
          "消失:XXX"    → 等待文字消失
          其他          → 默认作为文字等待
        """
        end = time.time() + timeout

        if condition.startswith("图像:"):
            target = condition[3:]
            while time.time() < end:
                if self._matcher.find(target, region=region):
                    return True
                time.sleep(interval)

        elif condition.startswith("消失:"):
            target = condition[3:]
            while time.time() < end:
                if not self._ocr.find_text(target, region=region):
                    return True
                time.sleep(interval)

        elif condition in ("稳定", "stable"):
            return self._detector.is_stable(region=region, duration=1.0)

        elif condition in ("变化", "change"):
            while time.time() < end:
                if self._detector.has_changed(region=region):
                    return True
                time.sleep(interval)

        else:
            # 默认: 文字等待（支持 "文字:XXX" 或直接文字）
            target = condition[3:] if condition.startswith("文字:") else condition
            result = self._ocr.wait_for_text(target, region=region, timeout=timeout, interval=interval)
            return result is not None

        return False


class AutoPopup:
    """自动弹窗处理"""

    # 常见关闭按钮文字
    CLOSE_KEYWORDS = ['x', '×', 'close', '关闭', '取消', 'dismiss', '忽略',
                      'confirm', '确定', 'yes', '是', 'no', '否', 'ok',
                      'got it', '知道了']

    def __init__(self, clicker: ClickTarget):
        self._clicker = clicker
        self._rules: List[dict] = []

    def register(self, detect_text: str, action_text: str, priority: int = 5):
        """注册弹窗规则"""
        self._rules.append({
            "detect": detect_text,
            "action": action_text,
            "priority": priority,
        })
        self._rules.sort(key=lambda r: -r["priority"])

    def check_and_handle(self, ocr: OCREngine) -> bool:
        """检查并处理弹窗，返回是否处理了弹窗"""
        results = ocr.extract_all()
        texts = {r.text for r in results}
        for rule in self._rules:
            for t in texts:
                if rule["detect"].lower() in t.lower():
                    self._clicker.click(rule["action"], timeout=3.0)
                    time.sleep(0.3)
                    return True
        return False

    def close_by_text(self, text: str, timeout: float = 5.0) -> bool:
        """通过文字匹配关闭弹窗"""
        from perception.ocr import OCREngine
        ocr = OCREngine()
        return self._clicker.click(text, timeout=timeout)


class ActionHandler:
    """
    统一动作处理器（供执行器调用）
    实现所有 DSL 指令的底层动作
    """

    def __init__(self):
        self.ocr = OCREngine()
        self.matcher = TemplateMatcher()
        self.detector = ChangeDetector()
        self.clicker = ClickTarget(self.ocr, self.matcher)
        self.waiter = WaitCondition(self.ocr, self.matcher, self.detector)
        self.popup = AutoPopup(self.clicker)

        # 宏注册表
        self._macros: dict = {}
        self._register_builtin_macros()

    def __call__(self, action: str, **kwargs) -> Any:
        """执行器调用入口"""
        handlers = {
            "click": self._handle_click,
            "type": self._handle_type,
            "wait": self._handle_wait,
            "launch": self._handle_launch,
            "check_condition": self._handle_condition,
            "run_macro": self._handle_macro,
            "screenshot": self._handle_screenshot,
            "wait_screen_change": self._handle_wait_screen_change,
            "wait_screen_stable": self._handle_wait_screen_stable,
        }
        handler = handlers.get(action)
        if handler is None:
            raise ValueError(f"未知动作: {action}")
        return handler(**kwargs)

    def _handle_click(self, target: str, ctx=None, **_) -> bool:
        region = ctx.variables.get("region") if ctx else None
        return self.clicker.click(target, region=region)

    def _handle_wait(self, condition: str, timeout: float = 30.0, ctx=None, **_) -> bool:
        region = ctx.variables.get("region") if ctx else None
        return self.waiter.wait(condition, timeout=timeout, region=region)

    def _handle_type(self, text: str, ctx=None, **_) -> bool:
        HumanKeyboard.type_text(text)
        return True

    def _handle_launch(self, target: str, ctx=None, **_) -> bool:
        import subprocess
        subprocess.Popen(target, shell=True)
        return True

    def _handle_screenshot(self, dest: str = "", ctx=None, **_) -> dict:
        import base64, cv2
        img = ScreenCapture.capture()
        result = {"base64": "", "width": img.shape[1], "height": img.shape[0], "format": "png"}
        if dest:
            cv2.imwrite(dest, img)
            result["path"] = dest
        _, buf = cv2.imencode(".png", img)
        result["base64"] = base64.b64encode(buf).decode()
        return result

    def _handle_wait_screen_change(self, timeout: float = 30.0, ctx=None, **_) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            if self.detector.has_changed():
                return True
            time.sleep(0.3)
        return False

    def _handle_wait_screen_stable(self, timeout: float = 30.0, ctx=None, **_) -> bool:
        return self.detector.is_stable(duration=min(timeout, 2.0))

    def _handle_condition(self, condition: str, ctx=None, **_) -> bool:
        """执行条件判断"""
        # 颜色条件: COLOR H,S,V AT x,y,w,h [MIN_RATIO N]
        if condition.upper().startswith("COLOR "):
            return self._check_color_condition(condition)
        # 进度条类条件
        if "低于" in condition or "less than" in condition.lower():
            return self._check_threshold(condition, ctx)
        region = ctx.variables.get("region") if ctx else None
        result = self.ocr.find_text(condition, region=region)
        return result is not None

    def _check_color_condition(self, condition: str) -> bool:
        """COLOR H,S,V AT x,y,w,h [MIN_RATIO N]"""
        import re
        m = re.match(
            r"COLOR\s+([\d,.]+)\s+AT\s+([\d,]+)(?:\s+MIN_RATIO\s+([\d.]+))?",
            condition, re.IGNORECASE
        )
        if not m:
            return False
        hsv_parts = m.group(1).split(",")
        reg_parts = m.group(2).split(",")
        if len(hsv_parts) != 3 or len(reg_parts) != 4:
            return False
        h, s, v = int(hsv_parts[0]), int(hsv_parts[1]), int(hsv_parts[2])
        x, y, w, h = int(reg_parts[0]), int(reg_parts[1]), int(reg_parts[2]), int(reg_parts[3])
        min_ratio = float(m.group(3)) if m.group(3) else 0.1
        ratio = ColorDetector.detect_color((h, s, v), region=(x, y, w, h))
        return ratio >= min_ratio

    def _check_threshold(self, condition: str, ctx) -> bool:
        # 简单示例: 识别屏幕上的数值进度
        return random.random() < 0.3  # 实际应读取进度条

    def _handle_macro(self, macro_name: str, ctx=None, **_) -> bool:
        macro = self._macros.get(macro_name)
        if macro is None:
            raise ValueError(f"未找到宏: '{macro_name}'。已注册: {list(self._macros.keys())}")
        return macro(ctx)

    def register_macro(self, name: str, fn: Callable):
        self._macros[name] = fn

    def _register_builtin_macros(self):
        """内置宏"""
        import random as _rand

        def macro_fuben(ctx):
            """副本: 标准流程"""
            self.clicker.click("进入副本")
            self.waiter.wait("副本加载完成", timeout=30)
            self.clicker.click("开始战斗")
            self.waiter.wait("战斗结束", timeout=120)
            return True

        def macro_liurentask(ctx):
            """刷任务"""
            self.clicker.click("任务列表")
            time.sleep(0.5)
            self.clicker.click("接受任务")
            self.waiter.wait("任务完成", timeout=60)
            return True

        def macro_lingqu(ctx):
            """领取奖励"""
            self.clicker.click("领取奖励")
            time.sleep(0.3)
            self.popup.check_and_handle(self.ocr)
            self.clicker.click("确认")
            return True

        def macro_recover(ctx):
            """自动恢复"""
            self.clicker.click("恢复道具")
            time.sleep(0.3)
            self.clicker.click("使用")
            self.waiter.wait("恢复完成", timeout=10)
            return True

        self._macros["副本"] = macro_fuben
        self._macros["刷任务"] = macro_liurentask
        self._macros["领取奖励"] = macro_lingqu
        self._macros["自动恢复"] = macro_recover
