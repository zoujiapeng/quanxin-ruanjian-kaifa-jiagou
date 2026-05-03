"""
多模态融合感知功能注册
find_element / wait_element — 融合 OCR + 图像 + 无障碍树
"""
from features.registry import feature, P, TC, FeatureCategory as F
from features._utils import parse_region


@feature(
    name="find_element",
    display_name="融合定位元素",
    description="【融合感知】同时使用 OCR + 图像模板 + 无障碍树定位目标元素，返回置信度最高的结果。比单一策略更可靠。适用于任何需要定位屏幕元素的场景",
    category=F.PERCEPTION,
    params=[
        P("query", "str", "要查找的目标：文字内容 / 图像模板名", example="确定按钮"),
        P("region", "str", "搜索区域 'x,y,w,h'（可选）", required=False, default=""),
        P("threshold", "number", "匹配阈值 0-1", required=False, default=0.6),
    ],
    returns="dict{found, text, x, y, confidence, strategy} - 定位结果",
    test_cases=[
        TC("empty_query", {"query": ""}, "success",
           validator=lambda r: r.get("success") is True),
    ],
)
def find_element(query: str, region: str = "", threshold: float = 0.6) -> dict:
    try:
        from perception.fusion import get_fusion_engine
        engine = get_fusion_engine()
        reg = parse_region(region)
        result = engine.find_element(query, region=reg, threshold=threshold)
        if result.found:
            return {
                "found": True, "text": result.text,
                "x": result.x, "y": result.y, "w": result.w, "h": result.h,
                "confidence": result.confidence,
                "strategy": result.strategy,
                "strategies_tried": result.strategies_used,
                "center_x": result.center_x, "center_y": result.center_y,
            }
        return {"found": False, "strategies_tried": result.strategies_used}
    except ImportError:
        return {"found": False, "error": "融合引擎不可用"}


@feature(
    name="wait_element",
    display_name="等待元素出现",
    description="【融合感知】轮询等待目标元素出现，返回定位结果。用于等待动态加载的元素、弹窗、页面变化。替代固定秒数 WAIT，感知到即继续",
    category=F.PERCEPTION,
    params=[
        P("query", "str", "要等待的目标：文字 / 图像模板名", example="加载完成"),
        P("region", "str", "搜索区域 'x,y,w,h'（可选）", required=False, default=""),
        P("timeout", "number", "超时秒数", required=False, default=10),
        P("interval", "number", "轮询间隔秒数", required=False, default=0.5),
        P("threshold", "number", "匹配阈值 0-1", required=False, default=0.6),
    ],
    returns="dict{found, text, x, y, confidence, strategy} - 定位结果",
    test_cases=[
        TC("timeout", {"query": "__nonexistent__", "timeout": 1}, "success",
           validator=lambda r: r.get("success") and not r["result"]["found"]),
    ],
)
def wait_element(query: str, region: str = "", timeout: float = 10,
                 interval: float = 0.5, threshold: float = 0.6) -> dict:
    try:
        from perception.fusion import get_fusion_engine
        engine = get_fusion_engine()
        reg = parse_region(region)
        result = engine.wait_element(query, region=reg, timeout=timeout,
                                     interval=interval, threshold=threshold)
        if result.found:
            return {
                "found": True, "text": result.text,
                "x": result.x, "y": result.y, "w": result.w, "h": result.h,
                "confidence": result.confidence,
                "strategy": result.strategy,
                "strategies_tried": result.strategies_used,
                "center_x": result.center_x, "center_y": result.center_y,
            }
        return {"found": False, "strategies_tried": result.strategies_used}
    except ImportError:
        return {"found": False, "error": "融合引擎不可用"}
