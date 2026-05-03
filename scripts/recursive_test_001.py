"""递归测试 001: Lobster 自举验证
通过 pipe 发中文 prompt 到新 claude 实例，完成 GUI 自动化闭环"""
import subprocess, sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "\\..")

PROMPT = """\
你需要使用 lobster_* MCP 工具（共 107 个可用）完成以下 GUI 自动化任务。
请逐步执行每个步骤并报告结果。

步骤：
1. lobster_detect_process name="notepad.exe" → 检查记事本是否运行
2. 如果没运行 → lobster_launch_program target="notepad.exe"
3. lobster_focus_window title="Notepad" → 激活记事本窗口
4. lobster_type_text text="递归测试: Lobster 自举验证成功" → 输入文字
5. 等 1.5 秒
6. lobster_screenshot → 截图
7. lobster_ocr_find_text text="Lobster 自举验证" → 用 OCR 检查文字
8. 如果找到 → 报告 "【递归测试通过】Lobster 成功完成自举验证"
9. 如果没找到 → 报告 "【递归测试失败】OCR 未找到目标文字"
10. lobster_hotkey keys="alt+f4" → 关闭记事本
11. lobster_click_target target="不保存" → 点击不保存

这个任务需要 进程管理 + 窗口操作 + 键盘输入 + 截图 + OCR 的组合，
其他纯 CLI 项目做不到这种"启动→操作→感知→验证"闭环。
"""

result = subprocess.run(
    ["claude", "-p"],
    input=PROMPT,
    capture_output=True,
    text=True,
    encoding="utf-8",
    cwd=os.path.dirname(os.path.abspath(__file__)) + "\\..",
)

print("=== STDOUT ===")
print(result.stdout)
if result.stderr:
    print("=== STDERR ===")
    print(result.stderr[:2000])
print(f"\n=== EXIT CODE: {result.returncode} ===")
input("\n按 Enter 键关闭此窗口...")
