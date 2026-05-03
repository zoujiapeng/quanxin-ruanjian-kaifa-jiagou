"""
文件对话框功能
处理 Windows 文件打开/保存对话框 — 模拟键盘输入路径
"""
import time

from features.registry import feature, P, TC, FeatureCategory as F


def _type_path_and_confirm(path: str, timeout: float) -> bool:
    """通用：在文件对话框输入路径并确认"""
    try:
        import pyautogui
        import pyperclip
        # 等待对话框出现
        time.sleep(0.5)
        # Ctrl+A 选中当前内容 → 粘贴路径 → Enter
        old = pyperclip.paste()
        pyperclip.copy(path)
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)
        pyautogui.press("enter")

        # 如果出现覆盖确认对话框
        time.sleep(0.5)
        pyautogui.press("enter")
        # 恢复剪贴板
        try:
            pyperclip.copy(old)
        except Exception:
            pass
        return True
    except ImportError:
        return False


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
    tags=["dialog", "file"],
)
def filedialog_open(path: str, timeout: float = 10) -> dict:
    return {"success": True, "result": _type_path_and_confirm(path, timeout)}


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
    tags=["dialog", "file"],
)
def filedialog_save(path: str, overwrite: bool = True, timeout: float = 10) -> dict:
    return {"success": True, "result": _type_path_and_confirm(path, timeout)}


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
    tags=["dialog", "file"],
)
def filedialog_folder(path: str, timeout: float = 10) -> dict:
    return {"success": True, "result": _type_path_and_confirm(path, timeout)}


@feature(
    name="select_images",
    display_name="选择图片文件",
    description="""【交互·文件】弹出原生 Windows 文件选择对话框让用户选择图片文件（png/jpg/bmp）。

使用场景:
  - 用户说"选一张图"时调用此工具
  - 配合 IMAGE_CLICK 使用：选择图片 → 复制到模板目录 → 按名点击

选择后自动复制到 templates/ 目录并返回模板名。""",
    category=F.ACTION,
    params=[
        P("title", "str", "对话框标题", required=False, default="请选择图片文件"),
        P("multi_select", "boolean", "是否允许多选", required=False, default=False),
    ],
    returns="dict{success, files: [{path, name, template_name}], cancelled}",
)
def select_images(title: str = "请选择图片文件", multi_select: bool = False) -> dict:
    try:
        import tkinter as tk
        from tkinter import filedialog
        import shutil, os

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        filetypes = [("图片文件", "*.png *.jpg *.jpeg *.bmp"), ("所有文件", "*.*")]
        if multi_select:
            files = filedialog.askopenfilenames(title=title, filetypes=filetypes)
        else:
            files = filedialog.askopenfilename(title=title, filetypes=filetypes)

        root.destroy()

        if not files:
            return {"success": True, "files": [], "cancelled": True}

        # 复制到 templates/ 目录
        template_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "templates"))
        os.makedirs(template_dir, exist_ok=True)

        result_files = []
        for fp in files if isinstance(files, tuple) else [files]:
            name = os.path.splitext(os.path.basename(fp))[0]
            ext = os.path.splitext(fp)[1]
            dest = os.path.join(template_dir, f"{name}{ext}")
            shutil.copy2(fp, dest)
            result_files.append({
                "path": fp,
                "name": name,
                "template_name": name,
            })

        return {"success": True, "files": result_files, "cancelled": False}
    except ImportError:
        return {"success": False, "error": "tkinter 不可用"}
