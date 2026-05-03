"""
单一入口：导入所有功能模块（触发 @feature() 装饰器注册）。
所有需要全量注册的文件（server.py / mcp/server.py / tests）应仅引用此模块，
避免同样 20+ 行 import 在 4 个文件中重复。
"""
import features.action_features
import features.perception_features
import features.ai_debug_features
import features.system_features
import features.dsl_features
import features.input_features
import features.window_features
import features.system_control_features
import features.clipboard_features
import features.network_features
import features.timer_features
import features.filedialog_features
import features.a11y_features
import features.macro_features
import features.multimedia_features
import features.fusion_features
import features.persistence_features
import features.healing_features
import features.trigger_features
import features.ai_plan_features
import features.plugin_features
import features.browser_features
import features.state
import features.image_click_features
