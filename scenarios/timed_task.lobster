# ============================================================
# 定时任务测试实例 — 等待 → 启动程序 → 操作 → 记录
# ============================================================
# 用户场景:
#   "三分钟后打开计算器，算 1+2，然后在记事本里记录结果"
#
# 组合模式: 感知→动作→验证
#   OCR 找文字 → LAUNCH 启动程序 → 焦点切换 → CLICK 点击 → TYPE 输入
#
# 使用方式:
#   lobster run-file scenarios/timed_task.lobster
#   或
#   lobster run-sync "$(cat scenarios/timed_task.lobster)"
# ============================================================

# ── 第 1 步: 等 3 分钟 (180秒) ──
# LOOP 接收纯数字作为循环次数（新增特性）
# 使用 LOOP 而非 WAIT 180 的好处：可被 stop() 中断
LOOP 180
  WAIT 1
END

# ── 第 2 步: 启动计算器 ──
LAUNCH calc.exe
WAIT 2

# ── 第 3 步: 用 OCR 定位按钮并点击 ──
# 计算器按钮通过截图 + OCR 识别文字位置，再用坐标点击
# 注意：CLICK 参数可以是文字内容，由 click_target 功能自动用 OCR 定位
CLICK 1
CLICK +
CLICK 2
CLICK =

# 等计算结果出现
WAIT 2

# ── 第 4 步: 打开记事本记录 ──
LAUNCH notepad.exe
WAIT 2

# ── 第 5 步: 输入记录 ──
# TYPE 通过 type_text / type_clipboard 输入文字
TYPE 计算结果: 1 + 2 = 3
TYPE ---
TYPE 定时任务测试完成
TYPE 启动时间: 三分钟倒计时后自动执行

WAIT 1
