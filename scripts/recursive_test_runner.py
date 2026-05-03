"""
Lobster 独有能力演示 — 其他 AI 项目做不到的事

使用方法: python scripts/recursive_test_runner.py

这个脚本调用 Lobster 的感知层（screenshot/OCR）和交互层（窗口/输入），
这些都是纯 LLM 无法做到的。
"""
"""
Lobster 独有能力演示 — 其他 AI 项目做不到的事

使用方法: python scripts/recursive_test_runner.py

这个脚本调用 Lobster 的感知层（screenshot/OCR）和交互层（窗口/输入），
这些都是纯 LLM 无法做到的。

与其他方案对比:
  - 纯 LLM/Claude: 不能截图、不能 OCR、不能检测进程
  - AutoIt/PyAutoGUI: 能点界面但不能"读"屏幕文字
  - Playwright: 只能控制浏览器
  - Lobster: 感知→决策→动作闭环, 本地免token循环
"""
import sys
from pathlib import Path

# ── 修复 Windows 编码 ──
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── 加入 python 目录到路径 ──
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root / "python"))

# ── 初始化（触发所有 @feature 注册）──
import features._all  # noqa
from features.registry import registry


def print_result(step: str, data: dict, key: str = "result"):
    val = data.get(key, "N/A")
    if isinstance(val, (dict, list)):
        print(f"  → {str(val)[:200]}")
    else:
        print(f"  → {val}")
    print(f"  [耗时] {data.get('elapsed_ms', 0)}ms")


def main():
    print("=" * 54)
    print("  Lobster 独有能力演示 — 其他项目做不到的事")
    print("=" * 54)

    # ── 1. 进程检测 ──
    print("\n[1/5] 进程检测 — 纯 LLM 不可能做到")
    r = registry.execute("detect_process", name="notepad.exe")
    print_result("detect_process", r)
    running = r.get("result", False)

    # ── 2. 启动进程 ──
    if not running:
        print("\n[2/5] 启动程序 — Lobster 控制操作系统")
        r = registry.execute("launch_program", target="notepad.exe")
        print_result("launch_program", r, "success")
        import time
        time.sleep(1)

    # ── 3. 窗口激活 ──
    print("\n[3/5] 窗口控制 — 激活窗口并输入文字")
    r = registry.execute("focus_window", title="Notepad")
    print_result("focus_window", r)
    r = registry.execute("type_text", text="Lobster: 本地执行+感知闭环验证成功!")
    print_result("type_text", r)

    # ── 4. 截图 ──
    print("\n[4/5] 截图 — 读取屏幕内容")
    r = registry.execute("screenshot", region="full")
    img = r.get("result", {})
    print(f"  → 截图: {len(img.get('base64', ''))} bytes")
    print(f"  ⏱ {r.get('elapsed_ms', 0)}ms")

    # ── 5. OCR 文字提取 ──
    print("\n[5/5] OCR 文字识别 — 从截图中读取文字")
    r = registry.execute("ocr_extract_all")
    texts = r.get("result", [])
    print(f"  → 找到 {len(texts)} 段文字:")
    for t in texts[:8]:
        print(f"    \"{t.get('text', '')[:60]}\" ({(t.get('confidence', 0)):.0%})")
    print(f"  ⏱ {r.get('elapsed_ms', 0)}ms")
    print()

    print("=" * 54)
    print("  能力对比:")
    print("  ✅ 进程检测     — 纯 LLM / AutoIt / Playwright 做不到")
    print("  ✅ 窗口控制     — 纯 LLM 做不到")
    print("  ✅ 截图         — 纯 LLM 做不到")
    print("  ✅ OCR 文字识别  — 纯 LLM 做不到，AutoIt 做不到")
    print("  ✅ 全部本地执行  — 零 API token 消耗")
    print("=" * 54)
    return 0


if __name__ == "__main__":
    sys.exit(main())
