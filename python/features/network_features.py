"""
网络功能注册（待完善）
连接状态 / WiFi 管理
"""
from features.registry import feature, P, TC, FeatureCategory as F


@feature(
    name="network_status",
    display_name="获取网络状态",
    description="【网络】检测当前网络连接状态、类型（WiFi/以太网）、IP 地址等信息。用于确认网络可用性或诊断连接问题",
    category=F.SYSTEM,
    params=[],
    returns="dict{connected, type, ip, ssid} - 网络状态",
    tags=["待完善"],
)
def network_status() -> dict:
    return {"implemented": False, "description": "获取网络状态"}


@feature(
    name="wifi_list",
    display_name="列出 WiFi 网络",
    description="【网络】扫描并列出附近可用的 WiFi 网络名称和信号强度。用于选择要连接的网络",
    category=F.SYSTEM,
    params=[],
    returns="list[dict{ssid, signal, security}] - WiFi 列表",
    tags=["待完善"],
)
def wifi_list() -> list:
    return {"implemented": False, "description": "列出 WiFi 网络"}


@feature(
    name="wifi_connect",
    display_name="连接 WiFi",
    description="【网络】连接到指定的 WiFi 网络。用于切换网络连接",
    category=F.SYSTEM,
    params=[
        P("ssid", "str", "WiFi 名称", example="MyWiFi"),
        P("password", "str", "WiFi 密码", required=False, default=""),
    ],
    returns="bool - 是否连接成功",
    tags=["待完善"],
)
def wifi_connect(ssid: str, password: str = "") -> bool:
    return {"implemented": False, "description": "连接 WiFi"}


@feature(
    name="wifi_disconnect",
    display_name="断开 WiFi",
    description="【网络】断开当前 WiFi 连接。用于切换网络或节省电量",
    category=F.SYSTEM,
    params=[],
    returns="bool - 是否成功",
    tags=["待完善"],
)
def wifi_disconnect() -> bool:
    return {"implemented": False, "description": "断开 WiFi"}
