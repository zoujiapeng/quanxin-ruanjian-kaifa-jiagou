"""
Region Picker: 用户交互式框选屏幕区域

单窗口（根窗口全屏透明遮罩 + Canvas 绘制选区）
显示全屏半透明遮罩 → 用户拖拽 → 返回 (x, y, w, h)

其他 AI 项目做不到的事:
  - LLM: 不能看屏幕，更不能让用户"框选"区域
  - 传统自动化: 脚本写死了坐标，不能动态让用户定义
  - Lobster: Claude Code 请求 → 用户框选 → 引擎自动使用坐标监控
"""

from __future__ import annotations
import tkinter as tk
from typing import Optional, Tuple


class RegionPicker:
    """全屏交互式区域选择器（单窗口版）"""

    @staticmethod
    def pick(message: str = "请拖拽选择区域，按 ESC 取消") -> Optional[Tuple[int, int, int, int]]:
        """
        显示全屏透明遮罩，用户拖拽选择矩形区域

        Returns:
            (x, y, w, h) 或 None (取消)
        """
        result: list[Optional[Tuple[int, int, int, int]]] = [None]

        root = tk.Tk()
        root.attributes("-fullscreen", True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.4)  # 半透明
        root.configure(bg="black")
        root.title("Lobster Region Picker")
        root.focus_force()

        # Canvas 覆盖全屏
        canvas = tk.Canvas(root, highlightthickness=0, cursor="crosshair")
        canvas.pack(fill=tk.BOTH, expand=True)

        # 状态
        start_x, start_y = 0, 0
        rect_id = None
        label_id = None
        text_items = []

        def draw_hint():
            """在 Canvas 上绘制提示文字（白色，常亮）"""
            nonlocal text_items
            sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
            items = []
            items.append(canvas.create_text(
                sw // 2, 60,
                text=message,
                fill="white", font=("Microsoft YaHei", 22, "bold"),
                anchor="center",
            ))
            items.append(canvas.create_text(
                sw // 2, 100,
                text="拖拽选择区域 · ESC 取消",
                fill="#cccccc", font=("Microsoft YaHei", 14),
                anchor="center",
            ))
            text_items = items

        def on_mouse_down(event):
            nonlocal start_x, start_y, rect_id, label_id
            start_x, start_y = event.x_root, event.y_root
            if rect_id:
                canvas.delete(rect_id)
            if label_id:
                canvas.delete(label_id)
            rect_id = canvas.create_rectangle(
                start_x, start_y, start_x, start_y,
                outline="#00ff00", width=3, dash=(6, 3),
            )
            label_id = canvas.create_text(
                start_x + 10, start_y - 20,
                text=f"({start_x}, {start_y})",
                fill="#00ff00", font=("Arial", 13, "bold"),
                anchor="w",
            )

        def on_mouse_move(event):
            if rect_id:
                cx, cy = event.x_root, event.y_root
                canvas.coords(rect_id, start_x, start_y, cx, cy)
                canvas.coords(label_id, start_x + 10, start_y - 20)
                w, h = abs(cx - start_x), abs(cy - start_y)
                canvas.itemconfig(
                    label_id,
                    text=f"({start_x}, {start_y}) → ({cx}, {cy})  [{w}×{h}]",
                )

        def on_mouse_up(event):
            if rect_id:
                x1, y1, x2, y2 = start_x, start_y, event.x_root, event.y_root
                x, y = min(x1, x2), min(y1, y2)
                w, h = abs(x2 - x1), abs(y2 - y1)
                if w > 5 and h > 5:  # 忽略太小的选择
                    result[0] = (x, y, w, h)
            root.quit()
            root.destroy()

        def on_key(event):
            if event.keysym == "Escape":
                root.quit()
                root.destroy()

        # 绘制提示
        draw_hint()

        # 绑定事件
        canvas.tag_bind("all", "<ButtonPress-1>", on_mouse_down)
        root.bind("<ButtonPress-1>", on_mouse_down)
        root.bind("<B1-Motion>", on_mouse_move)
        root.bind("<ButtonRelease-1>", on_mouse_up)
        root.bind("<Escape>", on_key)

        try:
            root.mainloop()
        except Exception:
            pass

        return result[0]


if __name__ == "__main__":
    region = RegionPicker.pick("测试: 请框选一个区域")
    if region:
        x, y, w, h = region
        print(f"选中区域: ({x}, {y}) {w}×{h}")
    else:
        print("已取消")
