"""
模板捕获工具：框选屏幕区域 → 保存为模板图片（用于 IMAGE_FIND）

使用方式:
  python scripts/capture_template.py [模板名称]

流程:
  1. 弹出全屏区域选择器，用户框选要识别的图标/图片
  2. 自动截图保存到 templates/<模板名称>.png
  3. 输出保存路径和尺寸信息
"""

import sys, os, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def capture_template(name: str = "target"):
    from interaction.region_picker import RegionPicker
    from perception.vision import ScreenCapture
    import cv2

    region = RegionPicker.pick(f"请框选「{name}」图标区域，将保存为模板图片")
    if not region:
        print("已取消")
        return False

    x, y, w, h = region
    print(f"框选区域: ({x}, {y}) {w}×{h}")

    # 截图
    img = ScreenCapture.capture(region)
    tmpl_dir = os.path.join(PROJECT_DIR, "templates")
    os.makedirs(tmpl_dir, exist_ok=True)
    tmpl_path = os.path.join(tmpl_dir, f"{name}.png")
    cv2.imwrite(tmpl_path, img)

    print(f"模板已保存: {tmpl_path}  ({w}×{h})")
    return tmpl_path


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "target"
    result = capture_template(name)
    sys.exit(0 if result else 1)
