"""
感知类功能注册
OCR / 图像匹配 / 颜色检测 / 进度条 / 截图
"""
from features.registry import feature, P, TC, FeatureCategory as F
from features._utils import parse_region


@feature(
    name="ocr_find_text",
    display_name="OCR查找文字",
    description="【感知·定位】在屏幕或指定区域内用OCR查找文字，返回位置坐标(center_x/center_y)和置信度。用于定位按钮/文本后执行点击",
    category=F.PERCEPTION,
    params=[
        P("query", "str", "要查找的文字（支持模糊匹配）", example="开始游戏"),
        P("region", "str", "搜索区域 'x,y,w,h'（可选）", required=False, default=""),
        P("fuzzy_threshold", "number", "模糊匹配阈值 0-1", required=False, default=0.7),
    ],
    returns="dict{found, text, x, y, w, h, confidence}",
    test_cases=[
        TC("empty_query", {"query": ""}, "success",
           validator=lambda r: r.get("success") is True),
    ],
)
def ocr_find_text(query: str, region: str = "", fuzzy_threshold: float = 0.7):
    try:
        from perception.ocr import OCREngine
        engine = OCREngine()
        reg = parse_region(region)
        result = engine.find_text(query, region=reg, threshold=fuzzy_threshold)
        if result:
            x, y, w, h = result.bbox
            return {"found": True, "text": result.text, "x": x, "y": y, "w": w, "h": h,
                    "confidence": result.confidence,
                    "center_x": x + w // 2, "center_y": y + h // 2}
        return {"found": False}
    except ImportError:
        return {"found": False, "error": "OCR不可用"}


@feature(
    name="ocr_extract_all",
    display_name="OCR全文提取",
    description="【感知·全文】提取屏幕或区域内所有可见文字，返回带位置和置信度的列表。适用于数据采集、获取页面全部文本内容",
    category=F.PERCEPTION,
    params=[
        P("region", "str", "区域 'x,y,w,h'（可选）", required=False, default=""),
    ],
    returns="list[dict{text, x, y, confidence}]",
)
def ocr_extract_all(region: str = ""):
    try:
        from perception.ocr import OCREngine
        engine = OCREngine()
        reg = parse_region(region)
        results = engine.extract_all(reg)
        return [{"text": r.text, "x": r.bbox[0], "y": r.bbox[1], "confidence": r.confidence}
                for r in results]
    except ImportError:
        return []


@feature(
    name="find_image",
    display_name="图像模板匹配",
    description="【感知·模板】在屏幕中查找指定图像模板，支持多尺度匹配。用于查找图标/图片按钮等 OCR 无法识别的非文字元素",
    category=F.PERCEPTION,
    params=[
        P("template_name", "str", "模板图像名称（不含扩展名）", example="attack_button"),
        P("threshold", "number", "匹配阈值 0-1", required=False, default=0.8),
        P("region", "str", "搜索区域 'x,y,w,h'（可选）", required=False, default=""),
        P("find_all", "boolean", "是否查找所有匹配项", required=False, default=False),
    ],
    returns="dict{found, x, y, confidence} or list",
    test_cases=[
        TC("nonexistent", {"template_name": "__nonexistent__"}, "success",
           validator=lambda r: r.get("success") and not r["result"]["found"]),
    ],
)
def find_image(template_name: str, threshold: float = 0.8, region: str = "", find_all: bool = False):
    try:
        from perception.vision import TemplateMatcher
        matcher = TemplateMatcher()
        reg = parse_region(region)
        if find_all:
            results = matcher.find_all(template_name, threshold=threshold, region=reg)
            return [{"found": True, "x": pt[0], "y": pt[1], "confidence": conf}
                    for pt, conf in results]
        result = matcher.find(template_name, threshold=threshold, region=reg)
        if result:
            (x, y), conf = result
            return {"found": True, "x": x, "y": y, "confidence": conf}
        return {"found": False}
    except ImportError:
        return {"found": False, "error": "视觉模块不可用"}


@feature(
    name="detect_color",
    display_name="颜色检测",
    description="【感知·颜色】检测区域内指定 HSV 颜色的占比(0.0-1.0)。用于判断画面状态、检测指示灯颜色",
    category=F.PERCEPTION,
    params=[
        P("h", "number", "色相 Hue 0-179", example=120),
        P("s", "number", "饱和度 Saturation 0-255", example=200),
        P("v", "number", "亮度 Value 0-255", example=200),
        P("region", "str", "检测区域 'x,y,w,h'", required=False, default=""),
        P("tolerance", "number", "HSV容差", required=False, default=15),
    ],
    returns="float - 颜色占比 0.0~1.0",
)
def detect_color(h: int, s: int, v: int, region: str = "", tolerance: int = 15) -> float:
    try:
        from perception.vision import ColorDetector
        reg = parse_region(region)
        return ColorDetector.detect_color((h, s, v), tolerance=(tolerance,) * 3, region=reg)
    except ImportError:
        return 0.0


@feature(
    name="detect_progress",
    display_name="进度条检测",
    description="【感知·进度】自动识别区域内的进度条并返回填充比例(0.0-1.0)。用于等待安装/下载/加载完成的场景，替代固定秒数等待",
    category=F.PERCEPTION,
    params=[
        P("region", "str", "进度条区域 'x,y,w,h'（必填）"),
        P("direction", "str", "方向: horizontal|vertical|auto", required=False, default="auto"),
    ],
    returns="float - 进度 0.0~1.0",
)
def detect_progress(region: str, direction: str = "auto") -> float:
    try:
        from perception.vision import ColorDetector
        reg = parse_region(region)
        if reg is None:
            return 0.0
        return ColorDetector.detect_progress_bar(reg, direction=direction)
    except ImportError:
        return 0.0


@feature(
    name="screenshot",
    display_name="截图",
    description="【系统·截图】截取屏幕或区域截图，返回 base64 编码图像。分析场景用 jpeg（更小），文字识别用 png（无损）",
    category=F.SYSTEM,
    params=[
        P("region", "str", "截图区域 'x,y,w,h'（可选，默认全屏）", required=False, default=""),
        P("format", "str", "图像格式 jpeg|png", required=False, default="jpeg"),
        P("quality", "number", "JPEG质量 1-100", required=False, default=70),
    ],
    returns="dict{base64, width, height, format}",
    test_cases=[
        TC("fullscreen", {}, "non_null", skip_in_ci=True),
    ],
)
def screenshot(region: str = "", format: str = "jpeg", quality: int = 70):
    try:
        import base64, cv2
        from perception.vision import ScreenCapture
        reg = parse_region(region)
        img = ScreenCapture.capture(reg)
        h, w = img.shape[:2]
        if format == "jpeg":
            _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        else:
            _, buf = cv2.imencode(".png", img)
        b64 = base64.b64encode(buf).decode()
        return {"base64": b64, "width": w, "height": h, "format": format}
    except ImportError:
        return {"base64": "", "width": 0, "height": 0, "format": format, "error": "模拟模式"}


@feature(
    name="popup_close",
    display_name="关闭弹窗",
    description="【感知·弹窗】自动检测并关闭屏幕上的弹窗，支持 OCR 文字匹配关闭按钮。用于清理系统弹窗、广告、确认对话框",
    category=F.PERCEPTION,
    params=[
        P("text", "str", "要点击的按钮文字（可选，留空则自动检测）", required=False, default=""),
        P("timeout", "number", "超时秒数", required=False, default=5),
    ],
    returns="bool - 是否关闭了弹窗",
    test_cases=[
        TC("auto_close", {"text": "", "timeout": 2}, "success",
           validator=lambda r: r.get("success") is True, skip_in_ci=True),
    ],
)
def popup_close(text: str = "", timeout: float = 5) -> bool:
    try:
        from interaction.actions import ActionHandler, AutoPopup, ClickTarget
        from perception.ocr import OCREngine
        from perception.vision import TemplateMatcher
        ocr = OCREngine()
        matcher = TemplateMatcher()
        clicker = ClickTarget(ocr, matcher)
        popup = AutoPopup(clicker)
        if text:
            return popup.close_by_text(text, timeout=timeout)
        return popup.check_and_handle(ocr)
    except ImportError:
        return False


@feature(
    name="color_check",
    display_name="颜色检查",
    description="【感知·颜色判定】检测指定区域内是否包含目标颜色，返回 match/ratio 判断结果。效率高于 OCR，适合高频轮询状态变化",
    category=F.PERCEPTION,
    params=[
        P("h", "number", "色相 Hue 0-179", example=120),
        P("s", "number", "饱和度 Saturation 0-255", example=200),
        P("v", "number", "亮度 Value 0-255", example=200),
        P("region", "str", "检测区域 'x,y,w,h'"),
        P("tolerance", "number", "HSV容差", required=False, default=15),
        P("min_ratio", "number", "最小占比 0-1", required=False, default=0.1),
    ],
    returns="dict{match, ratio} - 是否匹配及颜色占比",
    test_cases=[
        TC("basic", {"h": 0, "s": 0, "v": 0, "region": "0,0,100,100"}, "success"),
    ],
)
def color_check(h: int, s: int, v: int, region: str, tolerance: int = 15, min_ratio: float = 0.1) -> dict:
    try:
        from perception.vision import ColorDetector
        from features._utils import parse_region
        reg = parse_region(region)
        if reg is None:
            return {"match": False, "ratio": 0.0, "error": "无效区域"}
        ratio = ColorDetector.detect_color((h, s, v), tolerance=(tolerance,) * 3, region=reg)
        return {"match": ratio >= min_ratio, "ratio": round(ratio, 3)}
    except ImportError:
        return {"match": False, "ratio": 0.0}
