# -*- coding: utf-8 -*-
"""
递归测试 005: 图像模板匹配 + 右键 — MCP 工具发现

流程:
  当前 Claude → 启动新 Claude (claude -p) → 新Claude通过MCP发现能力
  → 自主规划: lobster_region_select(框选) → 截图保存模板 → lobster_find_image(匹配)
  → lobster_click_target(右键)

运行方式:
  python scripts/recursive_test_image_click.py [目标名称]
"""

import sys, os, subprocess, json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
os.environ["PYTHONIOENCODING"] = "utf-8"

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def build_prompt(target: str) -> str:
    return f"""我现在需要你帮我用 LOBSTER 项目完成一个屏幕操作任务。

## 任务目标
桌面上有一个「{target}」图标，找到它并右键它。

## 步骤
### 1. 获取图标模板
先用 MCP 工具 `lobster_region_select` 让我用鼠标框选这个图标的区域。
我框选后你会得到坐标，然后请把该区域截图保存为模板文件。

模板路径: {PROJECT_DIR}/templates/{target}.png
可以用 Python 保存:
```python
from perception.vision import ScreenCapture
import cv2
img = ScreenCapture.capture((x, y, w, h))
cv2.imwrite(r'{PROJECT_DIR}\\templates\\{target}.png', img)
```

### 2. 搜索匹配
用 `lobster_find_image` 在整个桌面上搜索这个模板。

### 3. 右键点击
如果找到，用 `lobster_click_target` 点击坐标并右键。

## 项目路径
{PROJECT_DIR}
（.claude/settings.json 已配置 MCP，你不需要额外设置）

请开始执行，每一步都告诉我进展。"""


def run_test(target: str = "回收站"):
    print("=" * 60)
    print(f"递归测试 005: MCP 工具发现 + 框选 → 保存模板 → 匹配 → 右键")
    print(f"目标: {target}")
    print("=" * 60)

    prompt = build_prompt(target)

    print(f"发送给新 Claude 的请求:")
    print(f"---")
    # 只显示前200字
    short = prompt[:200] + "..." if len(prompt) > 200 else prompt
    print(short)
    print(f"---")

    print(f"\n启动新 Claude Code (claude -p)...")
    print(f"新 Claude 将通过 MCP 发现 lobster_region_select 等工具")
    print()

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["HOME"] = os.path.expanduser("~")

    result = subprocess.run(
        ["claude", "-p", prompt, "--dangerously-skip-permissions"],
        cwd=PROJECT_DIR,
        capture_output=True,
        timeout=300,
        env=env,
    )

    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")

    print(f"\n--- 新 Claude 输出 ---")
    safe = stdout.encode("gbk", errors="replace").decode("gbk", errors="replace")
    print(safe)

    if stderr.strip():
        print(f"\n--- stderr ---")
        safe = stderr[:2000].encode("gbk", errors="replace").decode("gbk", errors="replace")
        print(safe)
    print(f"\n退出码: {result.returncode}")

    # 保存结果
    log_path = os.path.join(PROJECT_DIR, "scripts", "_test_005_result.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"递归测试 005 结果\n")
        f.write(f"目标: {target}\n")
        f.write(f"返回码: {result.returncode}\n\n")
        f.write(stdout)
        if stderr.strip():
            f.write(f"\n\n--- stderr ---\n{stderr}")
    print(f"\n结果已保存: {log_path}")

    return result.returncode == 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "回收站"
    success = run_test(target)
    sys.exit(0 if success else 1)
