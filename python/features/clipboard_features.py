"""
剪贴板增强功能（待完善 → 已实现）
获取文本 / 图片 / 文件列表 / 清空 — 基于 pyperclip + win32clipboard
"""
import base64, io, os, time

from features.registry import feature, P, TC, FeatureCategory as F


@feature(
    name="clipboard_get_text",
    display_name="获取剪贴板文本",
    description="【剪贴板】读取当前剪贴板中的文本内容。用于捕获复制的内容",
    category=F.SYSTEM,
    params=[],
    returns="dict{success, result: str} - 剪贴板文本",
    tags=["clipboard"],
)
def clipboard_get_text() -> dict:
    try:
        import pyperclip
        text = pyperclip.paste()
        return {"success": True, "result": text}
    except ImportError:
        try:
            import win32clipboard
            import win32con
            win32clipboard.OpenClipboard()
            try:
                data = win32clipboard.GetClipboardData(win32con.CF_TEXT)
                text = data.decode("utf-8", errors="replace") if data else ""
            except TypeError:
                text = ""
            win32clipboard.CloseClipboard()
            return {"success": True, "result": text}
        except Exception as e:
            return {"success": False, "error": f"剪贴板读取失败: {e}"}


@feature(
    name="clipboard_get_image",
    display_name="获取剪贴板图片",
    description="【剪贴板】读取当前剪贴板中的图片，返回 base64 编码。用于保存截图复制的内容",
    category=F.SYSTEM,
    params=[
        P("format_", "str", "输出格式: base64|file", required=False, default="base64"),
        P("save_path", "str", "保存路径（format=file 时必填）", required=False, default=""),
    ],
    returns="dict{format, data, width, height} - 图片数据",
    tags=["clipboard"],
)
def clipboard_get_image(format_: str = "base64", save_path: str = "") -> dict:
    try:
        import win32clipboard
        from PIL import Image
        import win32con
        import io
        win32clipboard.OpenClipboard()
        try:
            handle = win32clipboard.GetClipboardData(win32con.CF_DIB)
            # 将 DIB 转为 PNG bytes
            from PIL import Image
            import struct
            # 解析 BITMAPINFOHEADER
            header_size = struct.unpack_from("<I", handle, 0)[0]
            width = struct.unpack_from("<i", handle, 4)[0]
            height = struct.unpack_from("<i", handle, 8)[0]
            bits = struct.unpack_from("<H", handle, 14)[0]
            # 简单转换：假定 32-bit BGRA
            if bits == 32:
                stride = width * 4
                pixel_offset = header_size
                pixel_data = handle[pixel_offset:]
                img = Image.frombytes("RGBA", (width, abs(height)), pixel_data)
                if height > 0:
                    img = img.transpose(Image.FLIP_TOP_BOTTOM)
            else:
                img = Image.open(io.BytesIO(handle[header_size:]))

            if format_ == "file" and save_path:
                img.save(save_path)
                result = {"format": "file", "path": save_path, "width": width, "height": abs(height)}
            else:
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                result = {"format": "base64", "data": b64, "width": width, "height": abs(height)}

            win32clipboard.CloseClipboard()
            return {"success": True, "result": result}
        except Exception:
            win32clipboard.CloseClipboard()
            return {"success": False, "error": "剪贴板中没有图片"}
    except ImportError:
        return {"success": False, "error": "需要 pywin32 + Pillow: pip install pywin32 Pillow"}


@feature(
    name="clipboard_get_files",
    display_name="获取剪贴板文件列表",
    description="【剪贴板】读取剪贴板中的文件路径列表。用于获取用户复制的文件信息",
    category=F.SYSTEM,
    params=[],
    returns="dict{success, result: list[str]} - 文件路径列表",
    tags=["clipboard"],
)
def clipboard_get_files() -> dict:
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        try:
            # CF_HDROP = 15
            handle = win32clipboard.GetClipboardData(15)
            # handle is a list of file paths already parsed by pywin32
            files = list(handle) if handle else []
            win32clipboard.CloseClipboard()
            return {"success": True, "result": files}
        except TypeError:
            win32clipboard.CloseClipboard()
            return {"success": True, "result": []}
    except ImportError:
        return {"success": False, "error": "需要 pywin32: pip install pywin32"}


@feature(
    name="clipboard_clear",
    display_name="清空剪贴板",
    description="【剪贴板】清空系统剪贴板内容。用于清除敏感信息或准备新内容",
    category=F.SYSTEM,
    params=[],
    returns="dict{success, result: bool} - 是否成功",
    tags=["clipboard"],
)
def clipboard_clear() -> dict:
    try:
        import pyperclip
        pyperclip.copy("")
        return {"success": True, "result": True}
    except ImportError:
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.CloseClipboard()
            return {"success": True, "result": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
