@echo off
cd /d "%~dp0.."
wt.exe -d "%CD%" claude "请使用 lobster_* MCP 工具完成以下 GUI 自动化任务。逐步执行并报告结果。步骤：1. lobster_detect_process name=notepad.exe 2. lobster_launch_program target=notepad.exe 3. lobster_focus_window title=Notepad 4. lobster_type_text text=递归测试：Lobster 自举验证成功 5. 等 1.5 秒 6. lobster_screenshot 7. lobster_ocr_find_text text=Lobster 自举验证 8. 如果找到报告通过 9. lobster_hotkey keys=alt+f4 10. lobster_click_target target=不保存"
