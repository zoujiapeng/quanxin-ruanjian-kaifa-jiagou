# ============================================================
# Lobster 独有能力演示 — 其他 AI 项目做不到的事
# ============================================================
#
# 为什么其他项目做不到:
#   纯 LLM: 不能截图、不能OCR、不能检测进程、不能控制窗口
#   AutoIt/PyAutoGUI: 能点界面但不会"读"屏幕
#   Playwright: 只能控制浏览器
#   SikuliX: 能做图匹配但脚本写死了
#
# Lobster 的独有能力:
#   1. 免 token 本地循环 (LOOP/WAIT/IF)
#   2. 截图 + OCR 读屏幕文字 (其他 LLM 做不到)
#   3. 进程/窗口检测与控制
#   4. 颜色检测 + 图像模板匹配
# ============================================================

# ── 第1步: 检测目标进程 ──
# (通过 CLI 调用，因为 perception 功能没有 DSL 关键字)
# python cli/lobster.py call detect_process name=notepad.exe

# ── 第2步: 启动程序（如未运行）──
# python cli/lobster.py call launch_program target=notepad.exe

# ── 第3步: 激活窗口并输入 ──
# python cli/lobster.py call focus_window title=Notepad
# python cli/lobster.py call type_text text="Lobster 本地引擎测试"

# ── 第4步: 截图 + OCR ──
# python cli/lobster.py call screenshot region=full
# python cli/lobster.py call ocr_find_text text="测试"

# ── 第5步: DSL 免 token 循环监控 ──
# 以下 LOOP 在本地引擎执行，每次迭代不消耗 API token
LOOP 监测
  WAIT 2
  # 检查条件（通过 CLI）
  # python cli/lobster.py call detect_color ...
  # 如果检测到变化则退出
  WAIT 1
END

WAIT 1
TYPE 演示完成
