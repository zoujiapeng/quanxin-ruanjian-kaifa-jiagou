"""
region_select: 让新 Claude Code 请求用户交互式框选屏幕区域

用法:
  python scripts/region_select.py "请框选进度条区域，用于监控安装进度"
  python scripts/region_select.py --json "请框选图标区域"  # JSON 格式输出 (默认)

输出 (stdout):
  {"x": 100, "y": 200, "w": 300, "h": 50}
  或
  取消  (用户按 ESC)

这是 Lobster 独有的能力:
  - 纯 LLM: 不能看屏幕，更不能让用户"框选"
  - 传统自动化: 坐标写死，不能动态交互
  - Lobster: Claude 请求 → 用户视觉框选 → JSON 坐标返回 → 后续自动化使用

依赖: tkinter (Python 标准库，无需额外安装)
"""

import sys, json, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from interaction.region_picker import RegionPicker


def main():
    message = "请拖拽选择监控区域，用于后续自动化操作"
    output_json = True

    args = sys.argv[1:]
    for a in args:
        if a == "--text":
            output_json = False
        elif a.startswith("--"):
            pass
        else:
            message = a

    region = RegionPicker.pick(message)

    if region is None:
        if output_json:
            print(json.dumps({"cancelled": True}))
        else:
            print("取消")
        sys.exit(0)

    x, y, w, h = region
    result = {"x": x, "y": y, "w": w, "h": h}

    if output_json:
        print(json.dumps(result))
    else:
        print(f"({x}, {y}) {w}x{h}")

    # 也写入环境变量文件，供后续 DSL 使用
    var_file = os.environ.get("LOBSTER_VAR_FILE")
    if var_file:
        with open(var_file, "w") as f:
            json.dump(result, f)


if __name__ == "__main__":
    main()
