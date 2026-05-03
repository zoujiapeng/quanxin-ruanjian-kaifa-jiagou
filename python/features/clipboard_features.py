"""
剪贴板增强功能注册（待完善）
获取文本 / 图片 / 文件列表 / 清空
"""
from features.registry import feature, P, TC, FeatureCategory as F


@feature(
    name="clipboard_get_text",
    display_name="获取剪贴板文本",
    description="【剪贴板】读取当前剪贴板中的文本内容。用于捕获复制的内容",
    category=F.SYSTEM,
    params=[],
    returns="str - 剪贴板文本",
    tags=["待完善"],
)
def clipboard_get_text() -> str:
    return {"implemented": False, "description": "获取剪贴板文本"}


@feature(
    name="clipboard_get_image",
    display_name="获取剪贴板图片",
    description="【剪贴板】读取当前剪贴板中的图片，返回 base64 编码。用于保存截图复制的内容",
    category=F.SYSTEM,
    params=[
        P("format", "str", "输出格式: base64|file", required=False, default="base64"),
        P("save_path", "str", "保存路径（format=file 时必填）", required=False, default=""),
    ],
    returns="dict{format, data, width, height} - 图片数据",
    tags=["待完善"],
)
def clipboard_get_image(format: str = "base64", save_path: str = "") -> dict:
    return {"implemented": False, "description": "获取剪贴板图片"}


@feature(
    name="clipboard_get_files",
    display_name="获取剪贴板文件列表",
    description="【剪贴板】读取剪贴板中的文件路径列表。用于获取用户复制的文件信息",
    category=F.SYSTEM,
    params=[],
    returns="list[str] - 文件路径列表",
    tags=["待完善"],
)
def clipboard_get_files() -> list:
    return {"implemented": False, "description": "获取剪贴板文件"}


@feature(
    name="clipboard_clear",
    display_name="清空剪贴板",
    description="【剪贴板】清空系统剪贴板内容。用于清除敏感信息或准备新内容",
    category=F.SYSTEM,
    params=[],
    returns="bool - 是否成功",
    tags=["待完善"],
)
def clipboard_clear() -> bool:
    return {"implemented": False, "description": "清空剪贴板"}
