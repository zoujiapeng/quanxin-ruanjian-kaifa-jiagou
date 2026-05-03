"""
文件对话框功能注册（待完善）
处理 Windows 文件打开/保存对话框
"""
from features.registry import feature, P, TC, FeatureCategory as F


@feature(
    name="filedialog_open",
    display_name="文件打开对话框",
    description="【对话框】在文件打开对话框中输入路径并确认。用于绕过手动选择文件，自动化文件打开操作",
    category=F.ACTION,
    params=[
        P("path", "str", "要打开的完整文件路径", example="C:\\文档\\report.docx"),
        P("timeout", "number", "等待对话框超时秒数", required=False, default=10),
    ],
    returns="bool - 是否成功",
    tags=["待完善"],
)
def filedialog_open(path: str, timeout: float = 10) -> bool:
    return {"implemented": False, "description": "在打开对话框中输入路径"}


@feature(
    name="filedialog_save",
    display_name="文件保存对话框",
    description="【对话框】在文件保存对话框中输入路径并确认。用于自动化保存操作",
    category=F.ACTION,
    params=[
        P("path", "str", "保存的完整文件路径", example="C:\\输出\\result.pdf"),
        P("overwrite", "boolean", "是否覆盖已存在文件", required=False, default=True),
        P("timeout", "number", "等待对话框超时秒数", required=False, default=10),
    ],
    returns="bool - 是否成功",
    tags=["待完善"],
)
def filedialog_save(path: str, overwrite: bool = True, timeout: float = 10) -> bool:
    return {"implemented": False, "description": "在保存对话框中输入路径"}


@feature(
    name="filedialog_folder",
    display_name="选择文件夹对话框",
    description="【对话框】在文件夹选择对话框中输入路径并确认。用于自动化选择目录操作",
    category=F.ACTION,
    params=[
        P("path", "str", "要选择的文件夹路径", example="C:\\目标文件夹"),
        P("timeout", "number", "等待对话框超时秒数", required=False, default=10),
    ],
    returns="bool - 是否成功",
    tags=["待完善"],
)
def filedialog_folder(path: str, timeout: float = 10) -> bool:
    return {"implemented": False, "description": "在文件夹选择对话框中输入路径"}
