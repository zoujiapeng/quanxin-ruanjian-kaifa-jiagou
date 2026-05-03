@echo off
cd /d "%~dp0.."
wt.exe -d "%CD%" claude "你的任务是执行 Lobster 项目的独有能力演示脚本。只需运行以下一个命令: python scripts/recursive_test_runner.py 然后报告运行结果。注意: 这个脚本会启动记事本、输入文字、截图和 OCR 识别。你只需执行这一个命令，不要做其他操作。"
