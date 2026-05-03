---
name: 递归测试-001
description: "用 Lobster 驱动新 Claude 实例完成 GUI 自动化闭环"
---

## 测试目标

验证 Lobster 能做到"其他项目做不到的事"——通过**新 Claude Code 实例**调用 Lobster 的 GUI 自动化能力，完成从"启动程序→操作→感知→验证"的完整闭环。

## 测试流程

```
当前 Claude Code (我)
    │  1. 设计 prompt（包含 GUI 自动化任务）
    │  2. pipe 到新 claude 实例
    ▼
新 Claude Code 实例
    │  3. 通过 MCP 发现 lobster_* 工具
    │  4. 调用工具链完成 GUI 任务
    │  5. 截图 + OCR 验证结果
    ▼
验证结果
    │  6. 新 Claude 报告成功/失败
```

## 测试 Prompt

发给新 Claude 的 prompt 内容——必须包含"感知→决策→动作→验证"闭环：

```
需要使用 Lobster MCP 工具完成 GUI 自动化任务。

1. 用 lobster_detect_process 检查 notepad.exe 是否在运行
2. 如果不在运行，用 lobster_launch_program 启动 notepad.exe (target="notepad.exe")
3. 用 lobster_focus_window 切换到记事本窗口 (title 含"记事本"或"Notepad")
4. 用 lobster_type_text 在记事本中输入 "递归测试: Lobster 自举验证成功"
5. 等待 1 秒（可以用时间或简单逻辑）
6. 用 lobster_screenshot 截图
7. 用 lobster_ocr_find_text 在截图中搜索 "Lobster 自举验证"
8. 如果 OCR 找到 → 向用户报告"递归测试通过"
9. 用 lobster_hotkey 按 Alt+F4 关闭记事本 (keys="alt+f4")
10. 用 lobster_click_target 点击"不保存"按钮 (target="不保存")

这步组合: 进程管理 + 窗口操作 + 键盘输入 + 截图 + OCR，
纯 CLI 工具做不到，但 Lobster 可以。
```

## 执行方式

```powershell
cd C:\Users\zou\Desktop\claude1
$prompt = @'
...prompt内容...
'@
$prompt | claude -p
```

## 预期结果

- 新 Claude 成功启动 lobster MCP 并发现工具
- 成功调用 detect_process → launch_program → focus_window → type_text → screenshot → ocr_find_text → hotkey
- OCR 验证通过，报告"递归测试通过"
- 记事本被关闭（不保存）
