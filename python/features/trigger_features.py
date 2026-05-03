"""
触发器管理功能注册
trigger_list_types / trigger_list / trigger_stop / trigger_stop_all
"""
from features.registry import feature, P, TC, FeatureCategory as F


@feature(
    name="trigger_list_types",
    display_name="列出触发器类型",
    description="【触发器】列出所有可用的触发器类型（文件/进程/窗口/剪贴板/网络）。用于了解可设置哪些事件监听",
    category=F.DEBUG,
    params=[],
    returns="list[dict{name, display_name, description, event_key}] - 触发器类型列表",
)
def trigger_list_types() -> list:
    try:
        from engine.triggers import list_trigger_types
        return list_trigger_types()
    except ImportError:
        return []


@feature(
    name="trigger_list",
    display_name="列出活跃触发器",
    description="【触发器】列出当前所有活跃的触发器实例及其状态。用于监控和管理正在运行的监听器",
    category=F.DEBUG,
    params=[],
    returns="list[dict{id, spec_name, config, status}] - 触发器实例列表",
)
def trigger_list() -> list:
    try:
        from engine.triggers import get_trigger_engine
        return get_trigger_engine().list_instances()
    except ImportError:
        return []


@feature(
    name="trigger_stop",
    display_name="停止触发器",
    description="【触发器】停止指定的触发器实例。用于取消不再需要的事件监听",
    category=F.DEBUG,
    params=[
        P("instance_id", "str", "触发器实例 ID", example="trg_1712345678_1"),
    ],
    returns="bool - 是否成功",
)
def trigger_stop(instance_id: str) -> bool:
    try:
        from engine.triggers import get_trigger_engine
        return get_trigger_engine().stop(instance_id)
    except ImportError:
        return False


@feature(
    name="trigger_stop_all",
    display_name="停止所有触发器",
    description="【触发器】停止所有正在运行的触发器实例。用于紧急清理或重置监听状态",
    category=F.DEBUG,
    params=[],
    returns="bool - 是否成功",
)
def trigger_stop_all() -> bool:
    try:
        from engine.triggers import get_trigger_engine
        get_trigger_engine().stop_all()
        return True
    except ImportError:
        return False


@feature(
    name="trigger_get",
    display_name="查看触发器详情",
    description="【触发器】查看指定触发器实例的详细信息和状态",
    category=F.DEBUG,
    params=[
        P("instance_id", "str", "触发器实例 ID"),
    ],
    returns="dict{id, spec_name, config, status, fired_count, ...} - 触发器详情",
)
def trigger_get(instance_id: str) -> dict:
    try:
        from engine.triggers import get_trigger_engine
        result = get_trigger_engine().get_instance(instance_id)
        return result or {"error": "触发器不存在"}
    except ImportError:
        return {"error": "触发器模块不可用"}
