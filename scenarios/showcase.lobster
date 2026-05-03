# ============================================================
# Lobster 全能演示 — 其他 AI 项目绝对做不到的事
# ============================================================
#
# 这些能力全部在本地引擎执行，不需要 API token:
#   - 交互式区域框选 (REGION_SELECT) — 用户拖拽选区域
#   - 屏幕文字读取 (OCR_FIND/OCR_EXTRACT)
#   - 进度条检测 (IF PROGRESS x,y,w,h > 0.5)
#   - 图像模板匹配 (IF IMAGE template)
#   - 颜色检测条件判断 (IF COLOR)
#   - 截图保存 (SCREENSHOT)
#   - 等待屏幕变化/静止 (WAITSCREEN/SCREENSTABLE)
#   - 定时器触发 (WHEN TIMER_INTERVAL)
#   - 并行执行 (PARALLEL/WITH)
#   - 进程/窗口事件触发 (WHEN PROCESS_START/WINDOW_OPEN)
#   - 窗口聚焦/热键 (FOCUS/HOTKEY)
#   - 变量赋值 (SET) + 变量表达式 IF {var} > 5
#   - 带参数子程序 (SUBROUTINE/CALL)
#   - 免token循环监控 (LOOP/IF/BREAK)
#
# 对比其他方案:
#   - 纯 LLM: 不能读屏幕、不能点界面、不能循环
#   - 传统自动化(Selenium/AutoIt): 脚本死板，不能理解屏幕内容
#   - Playwright: 只能浏览器内，管不了桌面
#   - OCR工具(Tesseract): 只能识别文字，不能点不能决策
#   - 其他AI项目: 无法让用户交互式框选区域
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

# ── 场景10: 交互式区域框选 + 变量表达式 ──
# 这才是真正的杀手锏:
# Claude Code 说"请框选进度条区域" → 用户拖拽 → 引擎自动监控
# 其他 AI 项目一个都做不到这种交互
REGION_SELECT progress_region 请框选进度条区域，用于监控安装进度
IF {progress_region} != ""
  LOOP 区域监控
    WAIT 2
    IF PROGRESS {progress_region} > 0.8
      TYPE 进度已超过80%，即将完成
      SCREENSHOT nearly_done.png
    END
    IF PROGRESS {progress_region} > 0.99
      TYPE 安装完成！
      BREAK
    END
    IF {_loop_区域监控_count} > 30
      TYPE 监控超时，退出
      BREAK
    END
  END
END

# ── 场景11: OCR 文字读取 + 图像匹配 ──
# 读屏幕文字、找图标，全本地执行
REGION_SELECT text_region 请框选需要读取文字的区域
OCR_FIND 错误
IF _ocr_found
  SCREENSHOT error_detected.png
  TYPE 屏幕上发现"错误"文字，位置: ({_ocr_x}, {_ocr_y})
ELSE
  OCR_EXTRACT
  TYPE 当前屏幕文字已保存到变量 _ocr_texts
END

# ── 场景12: 窗口聚焦 + 热键操作 ──
FOCUS 记事本
WAIT 1
HOTKEY ctrl, a
WAIT 1
HOTKEY ctrl, c
TYPE 已全选并复制内容

WAIT 1
TYPE 全部演示已完成 — 所有操作均在本地引擎执行，零 token 消耗
