"""
融合感知引擎: 统一的多模态元素定位
同时使用 OCR + 图像模板匹配 + 无障碍树定位目标
返回置信度最高的融合结果
"""
from __future__ import annotations
import time
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, field


@dataclass
class FusionResult:
    found: bool = False
    text: str = ""
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    confidence: float = 0.0
    strategy: str = ""         # 哪个策略找到的: ocr | template | a11y
    strategies_used: list = field(default_factory=list)  # 尝试过的策略列表
    center_x: int = 0
    center_y: int = 0


class FusionEngine:
    """
    多模态融合引擎

    策略权重自适应调整：
    - 每次成功定位后，根据用户确认（或后续操作验证）更新策略权重
    - 权重高的策略在融合时获得更高优先级
    - 连续失败的策略自动降权
    """

    _strategy_weights = {
        "ocr": 0.5,
        "template": 0.3,
        "a11y": 0.2,
    }
    _strategy_attempts: dict = {}
    _strategy_successes: dict = {}
    _lock = None  # 简单锁防止并发问题

    def __init__(self):
        self._ocr_engine = None
        self._template_matcher = None
        self._a11y_engine = None
        self._init_backends()

    def _init_backends(self):
        try:
            from perception.ocr import OCREngine
            self._ocr_engine = OCREngine()
        except Exception:
            pass
        try:
            from perception.vision import TemplateMatcher
            self._template_matcher = TemplateMatcher()
        except Exception:
            pass
        # a11y engine — 待完善时懒加载
        self._a11y_available = False

    def _lazy_init_a11y(self):
        if self._a11y_available:
            return True
        try:
            # 尝试导入无障碍模块（如果已实现）
            from system.accessibility import AccessibilityTree
            self._a11y_engine = AccessibilityTree()
            self._a11y_available = True
            return True
        except ImportError:
            return False

    # ── 公开 API ─────────────────────────────────────────────────

    def find_element(self, query: str, region: Optional[Tuple[int, int, int, int]] = None,
                     threshold: float = 0.6) -> FusionResult:
        """
        统一元素查找：同时使用所有可用策略，返回最佳结果
        """
        candidates = []
        strategies_tried = []

        # 策略 1: OCR 文字匹配
        if self._ocr_engine:
            strategies_tried.append("ocr")
            try:
                ocr_result = self._ocr_engine.find_text(query, region=region, threshold=threshold)
                if ocr_result:
                    x, y, w, h = ocr_result.bbox
                    weight = self._strategy_weights.get("ocr", 0.5)
                    conf = ocr_result.confidence * weight
                    candidates.append({
                        "text": ocr_result.text, "x": x, "y": y, "w": w, "h": h,
                        "confidence": conf, "strategy": "ocr",
                        "center_x": x + w // 2, "center_y": y + h // 2,
                    })
            except Exception:
                pass

        # 策略 2: 图像模板匹配
        if self._template_matcher:
            strategies_tried.append("template")
            try:
                tm_result = self._template_matcher.find(query, region=region, threshold=threshold)
                if tm_result:
                    (x, y), conf = tm_result
                    weight = self._strategy_weights.get("template", 0.3)
                    candidates.append({
                        "text": query, "x": x, "y": y, "w": 0, "h": 0,
                        "confidence": conf * weight, "strategy": "template",
                        "center_x": x, "center_y": y,
                    })
            except Exception:
                pass

        # 策略 3: 无障碍树
        if self._lazy_init_a11y() and self._a11y_engine:
            strategies_tried.append("a11y")
            try:
                a11y_result = self._a11y_engine.find(query)
                if a11y_result:
                    weight = self._strategy_weights.get("a11y", 0.2)
                    candidates.append({
                        "text": a11y_result.get("name", query),
                        "x": a11y_result.get("x", 0),
                        "y": a11y_result.get("y", 0),
                        "w": a11y_result.get("w", 0),
                        "h": a11y_result.get("h", 0),
                        "confidence": a11y_result.get("confidence", 0.5) * weight,
                        "strategy": "a11y",
                        "center_x": a11y_result.get("x", 0) + a11y_result.get("w", 0) // 2,
                        "center_y": a11y_result.get("y", 0) + a11y_result.get("h", 0) // 2,
                    })
            except Exception:
                pass

        if not candidates:
            return FusionResult(found=False, strategies_used=strategies_tried)

        # 按置信度排序
        best = max(candidates, key=lambda c: c["confidence"])
        return FusionResult(
            found=True,
            text=best["text"], x=best["x"], y=best["y"],
            w=best["w"], h=best["h"],
            confidence=round(best["confidence"], 3),
            strategy=best["strategy"],
            strategies_used=strategies_tried,
            center_x=best["center_x"], center_y=best["center_y"],
        )

    def wait_element(self, query: str, region: Optional[Tuple[int, int, int, int]] = None,
                     timeout: float = 10, interval: float = 0.5,
                     threshold: float = 0.6) -> FusionResult:
        """等待元素出现，轮询直到超时"""
        start = time.time()
        while time.time() - start < timeout:
            result = self.find_element(query, region=region, threshold=threshold)
            if result.found:
                return result
            time.sleep(interval)
        return FusionResult(found=False, strategies_used=["ocr", "template", "a11y"])

    # ── 策略权重自适应 ──────────────────────────────────────────

    def report_success(self, strategy: str):
        """报告策略成功（供后续自适应权重调整）"""
        self._strategy_attempts.setdefault(strategy, 0)
        self._strategy_successes.setdefault(strategy, 0)
        self._strategy_attempts[strategy] += 1
        self._strategy_successes[strategy] += 1
        self._recalibrate_weights()

    def report_failure(self, strategy: str):
        """报告策略失败"""
        self._strategy_attempts.setdefault(strategy, 0)
        self._strategy_attempts[strategy] += 1
        self._recalibrate_weights()

    def _recalibrate_weights(self):
        """根据历史成功率调整权重"""
        total = sum(self._strategy_attempts.get(s, 0) for s in self._strategy_weights)
        if total < 10:  # 数据不足时不调整
            return
        for strategy in self._strategy_weights:
            attempts = self._strategy_attempts.get(strategy, 0)
            successes = self._strategy_successes.get(strategy, 0)
            if attempts > 0:
                rate = successes / attempts
                self._strategy_weights[strategy] = max(0.05, min(0.8, rate))
        # 归一化
        total_w = sum(self._strategy_weights.values())
        for s in self._strategy_weights:
            self._strategy_weights[s] /= total_w


# 全局单例
_fusion_engine: Optional[FusionEngine] = None


def get_fusion_engine() -> FusionEngine:
    global _fusion_engine
    if _fusion_engine is None:
        _fusion_engine = FusionEngine()
    return _fusion_engine
