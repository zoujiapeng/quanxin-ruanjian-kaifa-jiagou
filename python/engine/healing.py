"""
自愈管道: 执行失败时的智能恢复策略链
OCR 刷新 → a11y 替代 → 坐标偏移 → 上报
"""
from __future__ import annotations
import math
import time
import random
import traceback
from typing import Any, Callable, Optional, List, Tuple
from dataclasses import dataclass, field


@dataclass
class HealResult:
    success: bool = False
    strategy: str = ""
    result: Any = None
    error: str = ""
    details: list = field(default_factory=list)


@dataclass
class HealAttempt:
    strategy: str
    success: bool
    duration_ms: float
    error: str = ""


class HealingPipeline:
    """
    自愈管道: 按策略链尝试恢复

    默认策略链:
    1. retry — 简单重试（+截图刷新）
    2. a11y — 改用无障碍接口
    3. offset — 坐标偏移试探
    4. escalate — 上报失败（最后手段）

    每个策略都有历史可靠性评分，影响排序
    """

    def __init__(self, action_handler=None):
        self._action_handler = action_handler
        # 策略可靠性历史: {strategy_name: [bool, ...]}
        self._reliability: dict[str, list[bool]] = {}
        self._max_history = 50

    # ── 主入口 ──────────────────────────────────────────────────

    def heal(self, action: str, error: str, context: dict,
             retry_action: Callable) -> HealResult:
        """
        尝试从失败中恢复

        Args:
            action: 失败的动作名称 (click, wait, ...)
            error: 原始错误信息
            context: 执行上下文 (target, region, timeout, ...)
            retry_action: 重试函数，接收策略名字典参数

        Returns:
            HealResult
        """
        history = HealResult()
        strategies = self._build_strategy_chain(action, context)

        for strategy_name, strategy_fn in strategies:
            attempt_start = time.time()
            try:
                result = strategy_fn(context)
                elapsed_ms = (time.time() - attempt_start) * 1000
                if result is not None and result is not False:
                    history.success = True
                    history.strategy = strategy_name
                    history.result = result
                    history.details.append({
                        "strategy": strategy_name,
                        "success": True,
                        "duration_ms": round(elapsed_ms, 1),
                    })
                    self._record_reliability(strategy_name, True)
                    return history
                else:
                    elapsed_ms = (time.time() - attempt_start) * 1000
                    history.details.append({
                        "strategy": strategy_name,
                        "success": False,
                        "error": "策略返回空",
                        "duration_ms": round(elapsed_ms, 1),
                    })
                    self._record_reliability(strategy_name, False)
            except Exception as e:
                elapsed_ms = (time.time() - attempt_start) * 1000
                history.details.append({
                    "strategy": strategy_name,
                    "success": False,
                    "error": str(e),
                    "duration_ms": round(elapsed_ms, 1),
                })
                self._record_reliability(strategy_name, False)

        history.error = f"所有自愈策略失败 (action={action})"
        return history

    # ── 策略链构建 ──────────────────────────────────────────────

    def _build_strategy_chain(self, action: str, context: dict) -> list:
        """按可靠性排序构建策略链"""
        strategies = [
            ("retry", self._strategy_retry),
            ("a11y", self._strategy_a11y),
            ("offset", self._strategy_offset),
            ("escalate", self._strategy_escalate),
        ]
        # 按历史可靠性从高到低排序（escalate 始终最后）
        def sort_key(item):
            name, _ = item
            if name == "escalate":
                return 1.0  # 永远最后
            rate = self._get_reliability(name)
            return -rate  # 高的排前面
        strategies.sort(key=sort_key)
        return strategies

    # ── 各策略实现 ──────────────────────────────────────────────

    def _strategy_retry(self, context: dict) -> Any:
        """策略 1: 截图刷新后重试"""
        target = context.get("target", "")
        region = context.get("region")

        # 先刷新截图（清除 OCR 缓存）
        try:
            from perception.vision import ScreenCapture
            ScreenCapture._cache = {}  # 清除缓存
        except Exception:
            pass

        # 使用融合引擎重试
        try:
            from perception.fusion import get_fusion_engine
            engine = get_fusion_engine()
            result = engine.find_element(target, region=region)
            if result.found:
                return {"x": result.center_x, "y": result.center_y,
                        "strategy": "retry", "confidence": result.confidence}
        except Exception:
            pass
        return None

    def _strategy_a11y(self, context: dict) -> Any:
        """策略 2: 改用无障碍接口"""
        target = context.get("target", "")
        try:
            # 尝试通过无障碍树查找
            if self._action_handler:
                # a11y_click 通过无障碍接口直接点击
                result = self._action_handler("a11y_click", target=target)
                if result:
                    return {"strategy": "a11y", "result": result}
        except Exception:
            pass
        return None

    def _strategy_offset(self, context: dict) -> Any:
        """策略 3: 坐标偏移试探 — 8方向 × 4半径共32点逐个尝试"""
        target = context.get("target", "")
        action = context.get("action", "click")
        try:
            from perception.fusion import get_fusion_engine
            engine = get_fusion_engine()
            result = engine.find_element(target)
            if result.found:
                base_x, base_y = result.center_x, result.center_y
                for radius in [10, 20, 30, 50]:
                    for angle in range(0, 360, 45):
                        ox = int(base_x + radius * math.cos(math.radians(angle)))
                        oy = int(base_y + radius * math.sin(math.radians(angle)))
                        # 有 handler 时逐个尝试，成功即返回
                        if self._action_handler:
                            try:
                                hr = self._action_handler(action, target=target, x=ox, y=oy)
                                if hr:
                                    return {"x": ox, "y": oy, "strategy": "offset", "radius": radius}
                            except Exception:
                                continue
                        else:
                            return {"x": ox, "y": oy, "strategy": "offset", "radius": radius}
        except Exception:
            pass
        return None

    def _strategy_escalate(self, context: dict) -> Any:
        """策略 4: 上报失败——记录到 telemetry 供 Claude Code 分析"""
        # 记录失败上下文到 telemetry
        try:
            from engine.store import get_store
            store = get_store()
            store.log_telemetry(__import__("features.registry", fromlist=["TelemetryEntry"]).TelemetryEntry(
                feature_name=f"heal_fail_{context.get('action', 'unknown')}",
                duration_ms=0,
                success=False,
                error=context.get("error", "unknown"),
                strategy="escalate",
            ))
        except Exception:
            pass
        # 返回 None 表示无法恢复
        return None

    # ── 可靠性评分 ──────────────────────────────────────────────

    def _record_reliability(self, strategy: str, success: bool):
        if strategy not in self._reliability:
            self._reliability[strategy] = []
        self._reliability[strategy].append(success)
        # 限制历史长度
        if len(self._reliability[strategy]) > self._max_history:
            self._reliability[strategy] = self._reliability[strategy][-self._max_history:]

    def _get_reliability(self, strategy: str) -> float:
        history = self._reliability.get(strategy, [])
        if not history:
            return 0.5  # 初始中性
        return sum(history) / len(history)

    def get_reliability_report(self) -> dict:
        return {
            name: {
                "rate": round(self._get_reliability(name), 3),
                "samples": len(self._reliability.get(name, [])),
            }
            for name in ["retry", "a11y", "offset", "escalate"]
        }


# 全局单例
_healing_pipeline: Optional[HealingPipeline] = None


def get_healing_pipeline(action_handler=None) -> HealingPipeline:
    global _healing_pipeline
    if _healing_pipeline is None:
        _healing_pipeline = HealingPipeline(action_handler=action_handler)
    return _healing_pipeline
