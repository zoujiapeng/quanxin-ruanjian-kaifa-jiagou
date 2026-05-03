"""
插件管理功能注册
plugin_load / plugin_list / plugin_unload — 外部功能插件管理
"""
from features.registry import feature, P, TC, FeatureCategory as F, registry


@feature(
    name="plugin_load",
    display_name="加载插件",
    description="【插件】从外部 .py 文件动态加载功能插件。插件可以使用 @feature() 注册新功能，所有注册的功能自动获得 MCP/CLI/HTTP 支持",
    category=F.SYSTEM,
    params=[
        P("path", "str", "插件文件路径（.py）或目录路径", example="C:/plugins/my_plugin.py"),
        P("namespace", "str", "插件命名空间（可选）", required=False, default=""),
    ],
    returns="dict{success, features_loaded, module} - 加载结果",
)
def plugin_load(path: str, namespace: str = "") -> dict:
    return registry.load_plugin(path, namespace=namespace)


@feature(
    name="plugin_list",
    display_name="列出插件",
    description="【插件】列出所有已加载的外部功能插件",
    category=F.SYSTEM,
    params=[],
    returns="list[dict{name, path}] - 插件列表",
)
def plugin_list() -> list:
    return registry.plugins


@feature(
    name="plugin_unload",
    display_name="卸载插件",
    description="【插件】卸载指定名称的插件。插件注册的功能仍保留，但插件模块从内存中移除",
    category=F.SYSTEM,
    params=[
        P("name", "str", "插件名称或路径", example="my_plugin"),
    ],
    returns="bool - 是否成功",
)
def plugin_unload(name: str) -> bool:
    return registry.unload_plugin(name)
