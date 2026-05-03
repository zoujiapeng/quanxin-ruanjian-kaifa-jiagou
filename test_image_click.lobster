# 图像点击测试：框选截图 → 按优先级查找 → 点击
# 第一步：框选监控区域（可选，限制查找范围）
REGION_SELECT monitor_area 请框选监控区域（或按 ESC 跳过，全屏搜索）

# 第二步：框选目标图标，保存为模板
REGION_SELECT target_icon 请框选目标图标（例如回收站）
TEMPLATE_CAPTURE target_icon recycle_bin

# 第三步：按优先级查找并点击
# 先找 recycle_bin，找不到就尝试其他图标
IMAGE_CLICK recycle_bin, backup_icon sim=0.85
