"""
浏览器交互功能 — 通过 Playwright 实现
如果 Playwright 不可用，功能返回明确提示要求安装

安装: pip install playwright && playwright install chromium
"""
from features.registry import feature, P, TC, FeatureCategory as F

HAS_PLAYWRIGHT = False
_browser = None
_page = None

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    pass


def _get_page():
    """获取或创建浏览器页面（延迟初始化）"""
    global _browser, _page
    if _page is not None:
        return _page
    if not HAS_PLAYWRIGHT:
        return None
    try:
        pw = sync_playwright().start()
        _browser = pw.chromium.launch(headless=False)
        _page = _browser.new_page()
        return _page
    except Exception:
        return None


def _not_installed_msg() -> dict:
    return {
        "success": False,
        "error": "Playwright 未安装。运行: pip install playwright && playwright install chromium",
        "installed": False,
    }


@feature(
    name="browser_list_tabs",
    display_name="列出浏览器标签页",
    description="【浏览器·Playwright】列出当前浏览器所有打开的标签页。用于了解浏览器当前状态",
    category=F.ACTION,
    params=[],
    returns="list[dict] - 标签页列表",
    tags=["browser", "playwright"],
)
def browser_list_tabs() -> list:
    if not HAS_PLAYWRIGHT:
        return _not_installed_msg()
    try:
        page = _get_page()
        if page is None:
            return {"success": False, "error": "无法启动浏览器"}
        context = page.context
        tabs = []
        for p in context.pages:
            tabs.append({
                "title": p.title(),
                "url": p.url,
            })
        return {"success": True, "result": tabs}
    except Exception as e:
        return {"success": False, "error": str(e)}


@feature(
    name="browser_switch_tab",
    display_name="切换浏览器标签页",
    description="【浏览器·Playwright】按标题或序号切换到指定标签页。用于多标签页场景下切换工作上下文",
    category=F.ACTION,
    params=[
        P("target", "str", "标签页标题或序号（如 '1', '微信'）", example="微信"),
    ],
    returns="bool - 是否切换成功",
    tags=["browser", "playwright"],
)
def browser_switch_tab(target: str) -> bool:
    if not HAS_PLAYWRIGHT:
        return _not_installed_msg()
    try:
        page = _get_page()
        if page is None:
            return {"success": False, "error": "无法启动浏览器"}
        context = page.context
        pages = context.pages
        # 按序号切换
        if target.isdigit():
            idx = int(target) - 1
            if 0 <= idx < len(pages):
                pages[idx].bring_to_front()
                return {"success": True, "result": True}
            return {"success": False, "error": f"标签页序号超出范围: {target}"}
        # 按标题切换
        for p in pages:
            if target.lower() in p.title().lower():
                p.bring_to_front()
                return {"success": True, "result": True}
        return {"success": False, "error": f"未找到标题包含 '{target}' 的标签页"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@feature(
    name="browser_close_tab",
    display_name="关闭浏览器标签页",
    description="【浏览器·Playwright】关闭当前或指定标签页。用于清理不需要的标签页",
    category=F.ACTION,
    params=[
        P("target", "str", "要关闭的标签页标题（留空关闭当前）", required=False, default=""),
    ],
    returns="bool - 是否关闭成功",
    tags=["browser", "playwright"],
)
def browser_close_tab(target: str = "") -> bool:
    if not HAS_PLAYWRIGHT:
        return _not_installed_msg()
    try:
        page = _get_page()
        if page is None:
            return {"success": False, "error": "无法启动浏览器"}
        if not target:
            page.close()
            return {"success": True, "result": True}
        context = page.context
        for p in context.pages:
            if target.lower() in p.title().lower():
                p.close()
                return {"success": True, "result": True}
        return {"success": False, "error": f"未找到标题包含 '{target}' 的标签页"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@feature(
    name="browser_get_url",
    display_name="获取当前 URL",
    description="【浏览器·Playwright】获取当前标签页的 URL。用于确认当前页面",
    category=F.ACTION,
    params=[],
    returns="str - 当前 URL",
    tags=["browser", "playwright"],
)
def browser_get_url() -> str:
    if not HAS_PLAYWRIGHT:
        return _not_installed_msg()
    try:
        page = _get_page()
        if page is None:
            return {"success": False, "error": "无法启动浏览器"}
        return {"success": True, "result": page.url}
    except Exception as e:
        return {"success": False, "error": str(e)}


@feature(
    name="browser_navigate",
    display_name="导航到 URL",
    description="【浏览器·Playwright】打开指定 URL。用于导航到目标网页",
    category=F.ACTION,
    params=[
        P("url", "str", "完整 URL", example="https://example.com"),
    ],
    returns="bool - 是否导航成功",
    tags=["browser", "playwright"],
)
def browser_navigate(url: str) -> bool:
    if not HAS_PLAYWRIGHT:
        return _not_installed_msg()
    try:
        page = _get_page()
        if page is None:
            return {"success": False, "error": "无法启动浏览器"}
        page.goto(url, wait_until="domcontentloaded")
        return {"success": True, "result": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@feature(
    name="browser_refresh",
    display_name="刷新页面",
    description="【浏览器·Playwright】刷新当前页面。用于页面更新后重新加载",
    category=F.ACTION,
    params=[
        P("hard_reload", "boolean", "是否强制刷新（忽略缓存）", required=False, default=False),
    ],
    returns="bool - 是否成功",
    tags=["browser", "playwright"],
)
def browser_refresh(hard_reload: bool = False) -> bool:
    if not HAS_PLAYWRIGHT:
        return _not_installed_msg()
    try:
        page = _get_page()
        if page is None:
            return {"success": False, "error": "无法启动浏览器"}
        page.reload(wait_until="domcontentloaded")
        return {"success": True, "result": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@feature(
    name="browser_go_back",
    display_name="浏览器后退",
    description="【浏览器·Playwright】返回上一页。用于导航回退",
    category=F.ACTION,
    params=[],
    returns="bool - 是否成功",
    tags=["browser", "playwright"],
)
def browser_go_back() -> bool:
    if not HAS_PLAYWRIGHT:
        return _not_installed_msg()
    try:
        page = _get_page()
        if page is None:
            return {"success": False, "error": "无法启动浏览器"}
        page.go_back(wait_until="domcontentloaded")
        return {"success": True, "result": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
