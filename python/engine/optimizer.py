"""
Telemetry-driven DSL Optimizer
分析 ExecutionStore 中的 telemetry 数据，输出优化建议
"""
from __future__ import annotations
from typing import Optional


class TelemetryAnalyzer:
    """
    基于 telemetry 数据的 DSL 优化分析器

    能力:
    - 按功能聚合统计（成功率、平均耗时、错误模式）
    - 检测高频失败模式
    - 自动建议替代策略或参数调整
    """

    def __init__(self):
        self._store = None

    def _get_store(self):
        if self._store is None:
            from engine.store import get_store
            self._store = get_store()
        return self._store

    def analyze_feature(self, feature_name: str) -> dict:
        """分析单个功能的 telemetry 数据"""
        store = self._get_store()
        stats = store.get_feature_stats(feature_name)
        recent = store.get_telemetry(feature_name, limit=50)

        # 错误模式分析
        error_patterns = {}
        for entry in recent:
            err = entry.get("error", "")
            if err:
                # 按错误消息的前 60 个字符聚类
                key = err[:60]
                error_patterns[key] = error_patterns.get(key, 0) + 1

        # 耗时趋势（最近 10 次 vs 全部平均）
        recent_durations = [
            e.get("duration_ms", 0) for e in recent[:10] if e.get("success")
        ]
        trend = "stable"
        avg_duration = stats.get("avg_duration_ms", 0)
        if recent_durations:
            recent_avg = sum(recent_durations) / len(recent_durations)
            if avg_duration > 0:
                ratio = recent_avg / avg_duration
                if ratio > 1.3:
                    trend = "degrading"
                elif ratio < 0.7:
                    trend = "improving"

        return {
            "feature": feature_name,
            "stats": stats,
            "error_patterns": error_patterns,
            "trend": trend,
            "recent_samples": len(recent),
        }

    def analyze_all(self) -> dict:
        """分析所有有 telemetry 记录的功能"""
        store = self._get_store()
        overall = store.get_all_stats()

        # 获取所有有过调用的功能名
        features = []
        from features.registry import registry
        for spec in registry.all():
            stats = store.get_feature_stats(spec.name)
            if stats.get("total", 0) > 0:
                features.append(self.analyze_feature(spec.name))

        return {
            "overall": overall,
            "features": features,
            "feature_count": len(features),
        }

    def suggest_optimizations(self) -> list[dict]:
        """自动分析 telemetry 并给出优化建议"""
        store = self._get_store()
        suggestions = []

        from features.registry import registry
        for spec in registry.all():
            stats = store.get_feature_stats(spec.name)
            total = stats.get("total", 0)
            if total < 3:
                continue  # 数据不足

            success_rate = stats.get("success_rate", 1.0)
            avg_duration = stats.get("avg_duration_ms", 0)

            # 1. 高失败率
            if success_rate < 0.5 and total >= 5:
                # 查找替代功能
                alternatives = self._find_alternatives(spec.name)
                suggestions.append({
                    "type": "high_failure_rate",
                    "feature": spec.name,
                    "severity": "high",
                    "message": f"成功率 {success_rate:.0%} (共 {total} 次调用)",
                    "suggestion": f"建议检查可靠性，考虑使用替代功能: {', '.join(alternatives) if alternatives else '无'}" if success_rate < 0.3 else f"建议增加重试或检查参数",
                    "rate": success_rate,
                    "total_calls": total,
                })

            # 2. 高延迟
            if avg_duration > 5000 and success_rate > 0.5:
                suggestions.append({
                    "type": "high_latency",
                    "feature": spec.name,
                    "severity": "medium",
                    "message": f"平均耗时 {avg_duration:.0f}ms",
                    "suggestion": "建议考虑增大超时或使用异步执行",
                    "avg_duration_ms": avg_duration,
                })

            # 3. 低使用率但高价值
            if total < 5 and success_rate > 0.8 and avg_duration < 1000:
                suggestions.append({
                    "type": "underutilized",
                    "feature": spec.name,
                    "severity": "info",
                    "message": f"高成功率({success_rate:.0%})但仅使用 {total} 次",
                    "suggestion": "该功能可靠高效，建议在流程中优先使用",
                })

        suggestions.sort(key=lambda s: {"high": 0, "medium": 1, "info": 2}[s["severity"]])
        return suggestions

    def detect_failure_patterns(self) -> list[dict]:
        """检测 telemetry 中的常见错误模式"""
        store = self._get_store()
        patterns = []

        from features.registry import registry
        all_errors = {}
        for spec in registry.all():
            recent = store.get_telemetry(spec.name, limit=100)
            for entry in recent:
                err = entry.get("error", "")
                if err:
                    key = err[:80]
                    if key not in all_errors:
                        all_errors[key] = {"count": 0, "features": set(), "example": err}
                    all_errors[key]["count"] += 1
                    all_errors[key]["features"].add(spec.name)

        for err_key, info in sorted(all_errors.items(), key=lambda x: -x[1]["count"]):
            if info["count"] >= 3:  # 至少出现 3 次
                patterns.append({
                    "error_prefix": err_key,
                    "count": info["count"],
                    "affected_features": list(info["features"]),
                    "example": info["example"],
                })

        return patterns[:10]  # 返回前 10 个模式

    def _find_alternatives(self, feature_name: str) -> list[str]:
        """查找功能名称相似的替代功能"""
        from features.registry import registry
        alternatives = []
        base = feature_name.split("_")[0] if "_" in feature_name else feature_name
        for spec in registry.all():
            if spec.name != feature_name and spec.name.startswith(base):
                alternatives.append(spec.name)
        return alternatives[:3]
