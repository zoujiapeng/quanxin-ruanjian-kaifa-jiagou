"""
持久化功能注册
Checkpoint/Resume / Telemetry / Vault
"""
from features.registry import feature, P, TC, FeatureCategory as F


@feature(
    name="exec_list_checkpoints",
    display_name="列出执行断点",
    description="【持久化】列出所有已保存的执行断点，包含任务ID、状态和时间。用于查看可恢复的任务",
    category=F.DEBUG,
    params=[
        P("limit", "int", "最多返回条数", required=False, default=20),
    ],
    returns="list[dict] - 断点列表",
    tags=["persistence", "store"],
)
def exec_list_checkpoints(limit: int = 20) -> list:
    try:
        from engine.store import get_store
        return get_store().list_checkpoints(limit=limit)
    except ImportError:
        return []


@feature(
    name="exec_get_checkpoint",
    display_name="获取执行断点",
    description="【持久化】获取指定任务的执行断点详情，包含 DSL、状态、变量快照。用于检查和恢复任务",
    category=F.DEBUG,
    params=[
        P("task_id", "str", "任务ID"),
    ],
    returns="dict - 断点详情",
    tags=["persistence", "store"],
)
def exec_get_checkpoint(task_id: str) -> dict:
    try:
        from engine.store import get_store
        cp = get_store().get_checkpoint(task_id)
        if cp:
            return {
                "task_id": cp.task_id,
                "state": cp.state,
                "completed_indices": cp.completed_indices,
                "variables": cp.variables,
                "scope_count": cp.scope_count,
                "node_info": cp.node_info,
                "created_at": cp.created_at,
                "updated_at": cp.updated_at,
            }
        return {"found": False, "error": f"断点 '{task_id}' 不存在"}
    except ImportError:
        return {"error": "持久化模块不可用"}


@feature(
    name="exec_delete_checkpoint",
    display_name="删除执行断点",
    description="【持久化】删除指定任务的执行断点。用于清理已完成或不需要恢复的任务",
    category=F.DEBUG,
    params=[
        P("task_id", "str", "任务ID"),
    ],
    returns="bool - 是否成功",
    tags=["persistence", "store"],
)
def exec_delete_checkpoint(task_id: str) -> bool:
    try:
        from engine.store import get_store
        get_store().delete_checkpoint(task_id)
        return True
    except ImportError:
        return False


@feature(
    name="exec_telemetry_stats",
    display_name="执行统计",
    description="【持久化】获取执行统计信息：总调用次数、成功率、平均耗时。用于监控系统健康度和性能",
    category=F.DEBUG,
    params=[
        P("feature_name", "str", "功能名称（可选，仅查看单个功能统计）", required=False, default=""),
    ],
    returns="dict - 统计信息",
    tags=["persistence", "telemetry"],
)
def exec_telemetry_stats(feature_name: str = "") -> dict:
    try:
        from engine.store import get_store
        store = get_store()
        if feature_name:
            return store.get_feature_stats(feature_name)
        return store.get_all_stats()
    except ImportError:
        return {"error": "持久化模块不可用"}


@feature(
    name="exec_vault_set",
    display_name="存储敏感信息",
    description="【持久化】加密存储敏感信息（密码、Token 等）。用于自动化流程中安全引用凭据",
    category=F.SYSTEM,
    params=[
        P("key", "str", "键名", example="wechat_password"),
        P("value", "str", "敏感值", example="my_password"),
    ],
    returns="bool - 是否成功",
    tags=["persistence", "vault"],
)
def exec_vault_set(key: str, value: str) -> bool:
    try:
        from engine.store import get_store
        get_store().vault_set(key, value)
        return True
    except ImportError:
        return False


@feature(
    name="exec_vault_get",
    display_name="读取敏感信息",
    description="【持久化】读取已存储的敏感信息。用于流程中自动填充密码/Token。注意：返回值在日志中可能可见",
    category=F.SYSTEM,
    params=[
        P("key", "str", "键名", example="wechat_password"),
    ],
    returns="str - 存储的值（如不存在返回空字符串）",
    tags=["persistence", "vault"],
)
def exec_vault_get(key: str) -> str:
    try:
        from engine.store import get_store
        return get_store().vault_get(key) or ""
    except ImportError:
        return ""


@feature(
    name="exec_vault_list",
    display_name="列出存储键名",
    description="【持久化】列出所有已存储的敏感信息键名（不显示值）。用于查看有哪些凭据可用",
    category=F.SYSTEM,
    params=[],
    returns="list[str] - 键名列表",
    tags=["persistence", "vault"],
)
def exec_vault_list() -> list:
    try:
        from engine.store import get_store
        return get_store().vault_list_keys()
    except ImportError:
        return []
