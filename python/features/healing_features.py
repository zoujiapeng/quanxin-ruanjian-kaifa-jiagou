"""
自愈管道功能注册
heal_reliability / heal_history / heal_reset — 自愈系统诊断
"""
from features.registry import feature, P, TC, FeatureCategory as F


@feature(
    name="heal_reliability",
    display_name="自愈可靠性报告",
    description="【自愈】查看各恢复策略的历史可靠性评分。用于诊断自愈系统效果",
    category=F.DEBUG,
    params=[],
    returns="dict{strategy, rate, samples} - 各策略可靠性",
    tags=["healing", "diagnostic"],
)
def heal_reliability() -> dict:
    try:
        from engine.healing import get_healing_pipeline
        pipeline = get_healing_pipeline()
        return pipeline.get_reliability_report()
    except ImportError:
        return {"error": "自愈模块不可用"}


@feature(
    name="heal_history",
    display_name="自愈历史",
    description="【自愈】查看近期的自愈事件历史。用于诊断和调试自动化失败场景",
    category=F.DEBUG,
    params=[
        P("limit", "int", "返回条数", required=False, default=20),
    ],
    returns="list[dict] - 自愈事件列表",
    tags=["healing", "diagnostic"],
)
def heal_history(limit: int = 20) -> list:
    try:
        from engine.store import get_store
        return get_store().get_telemetry("heal_*", limit=limit)
    except ImportError:
        return []


@feature(
    name="heal_reset_stats",
    display_name="重置自愈统计",
    description="【自愈】重置自愈系统的可靠性统计数据。用于调试或清除旧数据",
    category=F.DEBUG,
    params=[],
    returns="bool - 是否成功",
    tags=["healing", "diagnostic"],
)
def heal_reset_stats() -> bool:
    try:
        from engine.healing import get_healing_pipeline
        pipeline = get_healing_pipeline()
        pipeline._reliability = {}
        return True
    except ImportError:
        return False
