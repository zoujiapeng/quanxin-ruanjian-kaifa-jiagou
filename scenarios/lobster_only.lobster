# ============================================================
# Lobster 独有能力 — 免 Token 循环监控
# ============================================================
# 场景: "监控安装过程，出现什么弹窗就点什么，直到完成"
#
# 为什么其他项目做不到:
#   - AutoIt/PyAutoGUI: 能循环点击，但不会用 OCR 读屏幕文字
#   - SikuliX: 能看图匹配，但脚本写死了，没有 AI 应变
#   - Playwright: 只能操作浏览器，管不了桌面弹窗
#   - 纯 AI (直接调 API): 每轮循环都要 API 调用 → 烧钱
#
# Lobster 方案:
#   1. Claude Code 看一眼截图 → 生成此 DSL（一次 token）
#   2. 本地引擎执行 LOOP → 后续零 token 消耗
#   3. IF + OCR 识别弹窗 → AI 只在新弹窗出现时介入
# ============================================================

# ── 免 token 循环监控 ──
# 以下 LOOP 在本地引擎执行，每次迭代不消耗 API token
LOOP 监控
  WAIT 3

  # 用 OCR 查找各种按钮（感知→决策→动作）
  IF 下一步
    CLICK 下一步
  ELSE
    IF 确定
      CLICK 确定
    ELSE
      IF 同意
        CLICK 同意
      ELSE
        IF 完成
          CLICK 完成
          WAIT 1
          TYPE 安装已自动完成
          BREAK
        ELSE
          IF 安装成功
            TYPE 验证通过
            BREAK
          END
        END
      END
    END
  END

  WAIT 1
END
