# ── 测试: 区域图标检测 + 右键 ──
# 流程: 截图 → 用户框选 → OCR识别 → 找到则右键

# Step 1: 先截一张全屏参考图
SCREENSHOT C:\Users\zou\Desktop\claude1\test_before.png

# Step 2: 用户框选要监控的屏幕区域
REGION_SELECT check_region 请框选要检查的区域（桌面图标区域）

# Step 3: 截取框选区域的画面
SCREENSHOT C:\Users\zou\Desktop\claude1\test_region.png

# Step 4: 提取该区域所有文字
OCR_EXTRACT

# Step 5: 查找特定文字（图标名称）
OCR_FIND 回收站

# Step 6: 如果找到，右键它
IF _ocr_found
  CLICK {_ocr_x},{_ocr_y} RIGHT
  TYPE 已在 ({_ocr_x}, {_ocr_y}) 位置右键 → 已弹出上下文菜单
  WAIT 1
  CLICK 属性 RIGHT
ELSE
  TYPE 未找到指定文字/图标
  TYPE 当前区域文字: {_ocr_texts}
END

SCREENSHOT C:\Users\zou\Desktop\claude1\test_after.png
TYPE 测试完成
