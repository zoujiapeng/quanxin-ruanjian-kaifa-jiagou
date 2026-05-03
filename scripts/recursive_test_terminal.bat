@echo off
cd /d "%~dp0.."
wt.exe -d "%CD%" claude "你只能使用 lobster_* MCP 工具完成任务。禁止使用 Bash、python、PowerShell 或任何 CLI 命令。你的每一步都必须是 MCP 工具调用。任务是测试本机 GUI 自动化能力，需要你逐步执行并报告。步骤：1. lobster_detect_process name=notepad.exe 检测记事本是否在运行 2. 如果没运行则 lobster_launch_program target=notepad.exe 3. lobster_focus_window title=Notepad 4. lobster_type_text text=递归测试001: Lobster MCP 自举成功 5. lobster_screenshot 截图 6. lobster_ocr_find_text text=递归测试 在截图中找文字 7. 报告找到结果（第几步找到、截图中有哪些文字）8. lobster_hotkey keys=alt+f4 9. lobster_click_target target=不保存"
