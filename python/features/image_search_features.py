"""
自然语言图片搜索：根据自然语言描述在本地搜索匹配的图片文件
用于 IMAGE_CLICK 工作流的第三种图片获取方式（口头说明）

工作流: 用户口头描述 → 关键词提取 → 文件名模糊匹配 → 返回排序结果
"""
import os
import re
from pathlib import Path
from difflib import SequenceMatcher

from features.registry import feature, P, TC, FeatureCategory as F

# 常见中文停用词 — 用户说"帮我找一个红色的按钮图片"时提取"红色""按钮"
_STOPWORDS = frozenset({
    "的", "了", "是", "在", "有", "我", "要", "个", "这", "那",
    "什么", "怎么", "如何", "一个", "这个", "那个", "可以", "需要",
    "把", "被", "和", "与", "及", "或", "而", "但", "也", "都",
    "就", "还", "很", "太", "更", "最", "不", "没", "好", "能",
    "会", "应该", "已经", "正在", "着", "过", "吗", "呢", "吧",
    "啊", "哦", "嗯",
    "图片", "图标", "图像", "文件", "按钮", "帮我", "找",
    "a", "an", "the", "is", "are", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "at", "this", "that", "it",
    "i", "me", "my", "you", "your", "he", "she", "it", "we", "they",
})
# 这些词保留为关键词（不拆分单字）
_KEEP_WORDS = frozenset({"进度条", "进度", "按钮", "图标", "回收站", "搜索", "关闭", "确定", "取消"})


def _extract_keywords(query: str) -> list[str]:
    """从自然语言描述中提取关键词

    "帮我找一个红色的回收站图标" → ["红色", "回收站"]
    "find the attack button image" → ["attack", "button"]
    """
    cleaned = re.sub(r'[^\w\s一-鿿]', ' ', query)
    parts = cleaned.split()
    keywords = []
    seen = set()

    for p in parts:
        p = p.strip().lower()
        if not p or p in _STOPWORDS:
            continue

        if p in _KEEP_WORDS:
            if p not in seen:
                keywords.append(p)
                seen.add(p)
        elif re.match(r'^[一-鿿]+$', p):
            # 中文词：整体加入
            if p not in seen:
                keywords.append(p)
                seen.add(p)
            # 双字及以上词也拆单字补充（覆盖文件名只含单字的情况）
            if len(p) >= 2:
                for ch in p:
                    if ch not in _STOPWORDS and ch not in seen:
                        keywords.append(ch)
                        seen.add(ch)
        else:
            # 英文/数字词
            if p not in seen:
                keywords.append(p)
                seen.add(p)

    return keywords


def _score_match(filename: str, keywords: list[str]) -> float:
    """计算文件名与关键词的匹配分数

    完全包含关键词: 10分
    模糊匹配 > 0.6: 5~8分
    多个关键词累加
    """
    name_lower = filename.lower().replace("_", " ").replace("-", " ")
    score = 0.0
    for kw in keywords:
        if kw in name_lower:
            score += 10.0
        else:
            ratio = SequenceMatcher(None, kw, name_lower).ratio()
            if ratio > 0.6:
                score += ratio * 8.0
    return score


@feature(
    name="search_images",
    display_name="自然语言搜索图片",
    description="""【搜索·图片】根据自然语言描述在本地搜索匹配的图片文件。

    这是 IMAGE_CLICK 图像点击工作流的第三种图片获取方式（口头说明）。
    当用户口头说"帮我点击回收站"但你没找到对应模板时，用此工具搜索本地已有图片。

    搜索范围: templates/ 目录及子目录下的 png/jpg/bmp 文件。
    支持中文和英文关键词匹配（基于文件名，自动提取关键词去停用词）。

    返回结果按匹配度从高到低排列，template_name 可直接用于 IMAGE_CLICK DSL。

    典型用法:
      Claude: "你说的'回收站'我搜一下本地有没有图片模板..."
      → search_images(query="回收站图标")
      → 返回 recycle_bin, 回收站, recycle_icon → 问用户用哪个
      → 用选中的模板名构造 IMAGE_CLICK

    此工具不需要 DSL 关键字，是纯 MCP 辅助工具。""",
    category=F.PERCEPTION,
    params=[
        P("query", "str", "自然语言描述，如'回收站图标'、'红色按钮'、'attack button'"),
        P("limit", "number", "最大返回结果数", required=False, default=10),
    ],
    returns="dict{success, results: [{name, path, template_name, score}], query}",
    examples=[
        "search_images query='回收站图标'",
        "search_images query='红色按钮' limit=5",
        "search_images query='attack button'",
    ],
    test_cases=[
        TC("empty_query", {"query": ""}, "success",
           validator=lambda r: r.get("success") is True),
    ],
)
def search_images(query: str, limit: int = 10) -> dict:
    try:
        keywords = _extract_keywords(query)
        if not keywords:
            return {
                "success": True,
                "results": [],
                "query": query,
                "note": "无法从描述中提取关键词，请描述得更具体些",
            }

        # 确定搜索目录：templates/ 是主目录
        base_dir = Path(__file__).resolve().parent.parent.parent  # python/ → 项目根
        templates_dir = base_dir / "templates"
        search_dirs = []
        if templates_dir.exists():
            search_dirs.append(templates_dir)

        # 扫描图片文件
        results = []
        for sd in search_dirs:
            for ext in ("*.png", "*.jpg", "*.jpeg", "*.bmp"):
                for fp in sorted(sd.rglob(ext)):
                    stem = fp.stem
                    score = _score_match(stem, keywords)
                    if score > 0:
                        # 计算相对于 templates/ 的模板名
                        try:
                            rel = fp.relative_to(templates_dir)
                            template_name = str(rel.with_suffix(""))
                        except ValueError:
                            template_name = stem
                        results.append({
                            "name": stem,
                            "path": str(fp.resolve()),
                            "template_name": template_name,
                            "score": round(score, 1),
                        })

        # 按分数降序排列
        results.sort(key=lambda r: r["score"], reverse=True)
        results = results[:limit]

        return {
            "success": True,
            "results": results,
            "total": len(results),
            "query": query,
            "keywords": keywords,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "query": query}
