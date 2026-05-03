"""
浏览器交互功能注册（待完善）
标签页管理 / 导航 / URL 获取
"""
from features.registry import feature, P, TC, FeatureCategory as F


@feature(
    name="browser_list_tabs",
    display_name="列出浏览器标签页",
    description="【浏览器】列出当前浏览器所有打开的标签页标题和 URL。用于了解浏览器当前状态",
    category=F.ACTION,
    params=[],
    returns="list[dict{title, url, active}] - 标签页列表",
    tags=["待完善"],
)
def browser_list_tabs() -> list:
    return {"implemented": False, "description": "列出浏览器标签页"}


@feature(
    name="browser_switch_tab",
    display_name="切换浏览器标签页",
    description="【浏览器】按标题或序号切换到指定浏览器标签页。用于多标签页场景下切换工作上下文",
    category=F.ACTION,
    params=[
        P("target", "str", "标签页标题（或序号 '1'/'2'）", example="微信"),
    ],
    returns="bool - 是否切换成功",
    tags=["待完善"],
)
def browser_switch_tab(target: str) -> bool:
    return {"implemented": False, "description": "切换浏览器标签页"}


@feature(
    name="browser_close_tab",
    display_name="关闭浏览器标签页",
    description="【浏览器】关闭当前或指定标签页。用于清理不需要的标签页",
    category=F.ACTION,
    params=[
        P("target", "str", "要关闭的标签页标题（留空关闭当前）", required=False, default=""),
    ],
    returns="bool - 是否关闭成功",
    tags=["待完善"],
)
def browser_close_tab(target: str = "") -> bool:
    return {"implemented": False, "description": "关闭浏览器标签页"}


@feature(
    name="browser_get_url",
    display_name="获取当前 URL",
    description="【浏览器】获取当前浏览器地址栏 URL。用于确认当前页面或记录操作上下文",
    category=F.ACTION,
    params=[],
    returns="str - 当前 URL",
    tags=["待完善"],
)
def browser_get_url() -> str:
    return {"implemented": False, "description": "获取当前 URL"}


@feature(
    name="browser_navigate",
    display_name="导航到 URL",
    description="【浏览器】在浏览器地址栏输入 URL 并导航。用于打开指定网页",
    category=F.ACTION,
    params=[
        P("url", "str", "完整 URL", example="https://example.com"),
    ],
    returns="bool - 是否导航成功",
    tags=["待完善"],
)
def browser_navigate(url: str) -> bool:
    return {"implemented": False, "description": "导航到 URL"}


@feature(
    name="browser_refresh",
    display_name="刷新页面",
    description="【浏览器】刷新当前页面（等效 F5）。用于页面更新后重新加载",
    category=F.ACTION,
    params=[
        P("hard_reload", "boolean", "是否强制刷新（忽略缓存）", required=False, default=False),
    ],
    returns="bool - 是否成功",
    tags=["待完善"],
)
def browser_refresh(hard_reload: bool = False) -> bool:
    return {"implemented": False, "description": "刷新页面"}


@feature(
    name="browser_go_back",
    display_name="浏览器后退",
    description="【浏览器】模拟浏览器后退按钮返回上一页。用于导航回退",
    category=F.ACTION,
    params=[],
    returns="bool - 是否成功",
    tags=["待完善"],
)
def browser_go_back() -> bool:
    return {"implemented": False, "description": "浏览器后退"}
