# 递归测试-001: Lobster 自举验证
# 描述: 用 Lobster 的 GUI 自动化能力完成"启动→操作→感知→验证"闭环
# 这是其他 CLI 自动化项目做不到的组合

LAUNCH notepad.exe
WAIT 1
FOCUS_WINDOW title="记事本"
TYPE_TEXT text="递归测试: Lobster 自举验证成功"
WAIT 1
SCREENSHOT
OCR_FIND text="Lobster 自举验证"
IF OCR_FOUND
    # 找到文字，测试通过
    HOTKEY keys="alt+f4"
    WAIT 0.5
    CLICK target="不保存"
END
