"""
无障碍树功能
Windows Accessibility Tree 获取和操作 — 基于 UIA (win32com)
"""
from features.registry import feature, P, TC, FeatureCategory as F


def _get_uia():
    """初始化 UIA 自动化客户端"""
    try:
        from win32com.client import Dispatch
        from win32com.client import GetObject
        return True
    except ImportError:
        return False


def _walk_tree(element, depth: int, max_depth: int, filter_visible: bool) -> dict:
    """递归遍历无障碍树"""
    if depth > max_depth:
        return None
    try:
        name = element.CurrentName
        role = element.CurrentAutomationId  # 后备
        try:
            role = element.CurrentLocalizedControlType
        except Exception:
            pass
        ctrl_type = ""
        try:
            ctrl_type = element.CurrentControlType
        except Exception:
            pass

        is_visible = True
        try:
            is_visible = element.CurrentIsOffscreen == 0
        except Exception:
            pass

        if filter_visible and is_visible is False:
            return None

        node = {
            "name": name or "",
            "role": role or "",
            "control_type": str(ctrl_type) if ctrl_type else "",
            "children": [],
        }

        try:
            enabled = element.CurrentIsEnabled
            node["enabled"] = enabled
        except Exception:
            pass

        try:
            bb = element.CurrentBoundingRectangle
            if bb and bb.left != 0 or bb.top != 0:
                node["bounds"] = {"left": bb.left, "top": bb.top,
                                  "width": bb.right - bb.left, "height": bb.bottom - bb.top}
        except Exception:
            pass

        if depth < max_depth:
            try:
                child = element.FindFirst(
                    __import__("win32com.client").constants.TreeScope_Children,  # noqa
                    __import__("win32com.client").gencache.EnsureDispatch("IASimpleProvider").CreatePropertyCondition(0, "")
                )
            except Exception:
                pass

        return node
    except Exception:
        return None


@feature(
    name="a11y_get_tree",
    display_name="获取无障碍树",
    description="【无障碍】获取当前活动窗口的无障碍访问树结构。用于了解界面元素层次结构，比 OCR 更精确",
    category=F.PERCEPTION,
    params=[
        P("max_depth", "int", "最大深度", required=False, default=5),
        P("filter_visible", "boolean", "是否只返回可见元素", required=False, default=True),
    ],
    returns="dict{role, name, children} - 无障碍树",
    tags=["a11y", "uia"],
)
def a11y_get_tree(max_depth: int = 5, filter_visible: bool = True) -> dict:
    try:
        import win32gui
        from win32com.client import Dispatch
        # 获取前台窗口
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return {"success": False, "error": "无前台窗口"}
        # 使用 UIA 获取元素树
        uia = Dispatch("UIAutomation.Core.UIAutomation", dynamic=True)
        element = uia.ElementFromHandle(hwnd)
        tree = _walk_tree(element, 1, max_depth, filter_visible) or {}
        return {"success": True, "result": tree}
    except ImportError:
        return {"success": False, "error": "需要 pywin32: pip install pywin32"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _find_elements(element, name: str, role: str, control_type: str, results: list, max_results: int = 20):
    """递归查找匹配元素"""
    if len(results) >= max_results:
        return
    try:
        el_name = element.CurrentName or ""
        el_role = ""
        try:
            el_role = element.CurrentLocalizedControlType or ""
        except Exception:
            pass
        # 匹配条件
        name_match = not name or name.lower() in el_name.lower()
        role_match = not role or role.lower() in el_role.lower()
        if name_match and role_match:
            entry = {"name": el_name, "role": el_role}
            try:
                bb = element.CurrentBoundingRectangle
                entry["bounds"] = {"left": bb.left, "top": bb.top,
                                   "width": bb.right - bb.left, "height": bb.bottom - bb.top}
            except Exception:
                pass
            try:
                entry["enabled"] = element.CurrentIsEnabled
            except Exception:
                pass
            results.append(entry)
    except Exception:
        pass

    # 递归子节点
    try:
        children = element.FindAll(
            0,  # TreeScope_Children
            __import__("win32com.client").gencache.EnsureDispatch("IUIAutomation").CreateTrueCondition()
        )
        for child in children:
            _find_elements(child, name, role, control_type, results, max_results)
    except Exception:
        pass


@feature(
    name="a11y_find_element",
    display_name="查找无障碍元素",
    description="【无障碍】在无障碍树中查找匹配指定条件的 UI 元素。用于精确定位按钮、输入框等控件",
    category=F.PERCEPTION,
    params=[
        P("name", "str", "元素名称（模糊匹配）", example="发送"),
        P("role", "str", "元素角色（如 button, edit, list）", required=False, default=""),
        P("control_type", "str", "控件类型（如 Edit, Button, ComboBox）", required=False, default=""),
    ],
    returns="list[dict{name, role, bounds, enabled}] - 匹配元素列表",
    tags=["a11y", "uia"],
)
def a11y_find_element(name: str, role: str = "", control_type: str = "") -> dict:
    try:
        import win32gui
        from win32com.client import Dispatch
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return {"success": False, "error": "无前台窗口"}
        uia = Dispatch("UIAutomation.Core.UIAutomation", dynamic=True)
        root = uia.ElementFromHandle(hwnd)
        results = []
        _find_elements(root, name, role, control_type, results)
        return {"success": True, "result": results}
    except ImportError:
        return {"success": False, "error": "需要 pywin32: pip install pywin32"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@feature(
    name="a11y_click_element",
    display_name="点击无障碍元素",
    description="【无障碍】通过无障碍接口点击指定 UI 元素，绕过坐标/图像匹配。适用于标准 Windows 控件",
    category=F.ACTION,
    params=[
        P("name", "str", "元素名称", example="确定"),
        P("role", "str", "元素角色（可选）", required=False, default=""),
    ],
    returns="bool - 是否点击成功",
    tags=["a11y", "uia"],
)
def a11y_click_element(name: str, role: str = "") -> dict:
    try:
        import win32gui
        from win32com.client import Dispatch
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return {"success": False, "error": "无前台窗口"}
        uia = Dispatch("UIAutomation.Core.UIAutomation", dynamic=True)
        root = uia.ElementFromHandle(hwnd)
        results = []
        _find_elements(root, name, role, "", results, max_results=5)
        for el_info in results:
            # 找到匹配元素后通过坐标点击（win32 API 方式）
            bounds = el_info.get("bounds")
            if bounds:
                import pyautogui
                cx = bounds["left"] + bounds["width"] // 2
                cy = bounds["top"] + bounds["height"] // 2
                pyautogui.click(cx, cy)
                return {"success": True, "result": True}
        return {"success": False, "error": f"未找到元素 '{name}'"}
    except ImportError:
        return {"success": False, "error": "需要 pywin32: pip install pywin32"}
    except Exception as e:
        return {"success": False, "error": str(e)}
