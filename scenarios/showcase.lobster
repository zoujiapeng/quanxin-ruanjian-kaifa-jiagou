# ============================================================
# Lobster 全能演示 — 其他 AI 项目绝对做不到的事
# ============================================================
#
# 这些能力全部在本地引擎执行，不需要 API token:
#   - 颜色检测条件判断 (IF COLOR)
#   - 截图保存 (SCREENSHOT)
#   - 等待屏幕变化/静止 (WAITSCREEN/SCREENSTABLE)
#   - 定时器触发 (WHEN TIMER_INTERVAL)
#   - 并行执行 (PARALLEL/WITH)
#   - 进程/窗口事件触发 (WHEN PROCESS_START/WINDOW_OPEN)
#   - 带参数子程序 (SUBROUTINE/CALL)
#   - 免token循环监控 (LOOP/IF/BREAK)
#
# 对比其他方案:
#   - 纯 LLM: 不能读屏幕、不能点界面、不能循环
#   - 传统自动化(Selenium/AutoIt): 脚本死板，不能理解屏幕内容
#   - Playwright: 只能浏览器内，管不了桌面
# ============================================================


# ── 子程序: 带参数的通用点击模块 ──
SUBROUTINE safe_click(target, timeout)
  LOOP 重试
    IF COLOR 0,0,0 AT 0,0,10,10  # 检测屏幕是否开启（空检测，占位）
      CLICK {target}
      WAIT 1
      BREAK
    ELSE
      WAIT 1
    END
  END
END

# ── 场景1: 截图存档 ──
# 纯本地操作，不需要 LLM 参与
SCREENSHOT step1_before.png
WAIT 1
CLICK 打开程序
WAIT 3
SCREENSHOT step2_after.png

# ── 场景2: 等待视觉变化 ──
# 等待画面变化（如安装界面跳转）
WAITSCREEN 30

# ── 场景3: 循环监控 + 颜色检测 ──
# 核心价值: LOOP 在本地引擎跑，零 token 消耗
LOOP 监控进度
  WAIT 2

  # 检测绿色指示灯 (HSV: 120,200,200)
  IF COLOR 120,200,200 AT 100,100,50,50 MIN_RATIO 0.3
    CLICK 完成
    BREAK
  ELSE
    # 检测红色错误指示灯 (HSV: 0,200,200)
    IF COLOR 0,200,200 AT 100,100,50,50 MIN_RATIO 0.2
      SCREENSHOT error_state.png
      TYPE 出现错误，请检查
      BREAK
    ELSE
      WAIT 3
    END
  END
END

# ── 场景4: 等待屏幕静止后操作 ──
# 确保页面完全渲染后再点击
SCREENSTABLE 15
CLICK 确认

# ── 场景5: 子程序调用 ──
CALL safe_click("下一步", 10)
CALL safe_click("安装", 30)

# ── 场景6: 定时器事件 ──
# 每 60 秒检查一次状态（注册后异步运行）
WHEN TIMER_INTERVAL 60
  SCREENSHOT periodic_check.png
  # 检测绿色状态灯
  IF COLOR 120,200,200 AT 0,0,100,100 MIN_RATIO 0.5
    TYPE 状态正常
  ELSE
    SCREENSHOT alert.png
  END
END

# ── 场景7: 进程事件触发 ──
# 当 notepad.exe 启动时自动执行
WHEN PROCESS_START notepad.exe
  WAIT 1
  TYPE 记事本已由 Lobster 自动检测到
  WAIT 1
  CLICK 保存
END

# ── 场景8: 并行任务 ──
# 同时监控多个状态
PARALLEL
  # 分支1: 监控安装进度
  LOOP 安装
    WAIT 3
    IF 下一步
      CLICK 下一步
      BREAK
    END
  END

  WITH
    # 分支2: 监控超时
    LOOP 超时检查
      WAIT 1
      IF 取消
        TYPE 操作超时
        BREAK
      END
    END
  END
END

# ── 场景9: 完整的免 token 监控循环 ──
# 这才是 Lobster 的核心竞争力:
# 一个 LOOP 在本地跑无数轮，不消耗一分钱 API token
LOOP 免token循环监控
  SCREENSHOT monitor.png

  # 检查运行状态
  IF COLOR 60,200,200 AT 200,200,80,80 MIN_RATIO 0.4
    TYPE 〖运行中〗
    WAIT 5
  ELSE
    IF COLOR 0,200,200 AT 200,200,80,80 MIN_RATIO 0.4
      SCREENSHOT failure.png
      TYPE 〖检测到异常〗
      BREAK
    ELSE
      IF 完成
        TYPE 〖任务完成〗
        BREAK
      ELSE
        WAIT 10
      END
    END
  END
END

WAIT 1
TYPE 所有演示已完成
