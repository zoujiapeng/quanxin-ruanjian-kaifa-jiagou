"""
网络功能
连接状态 / WiFi 管理 — 基于 Windows netsh + socket
"""
import socket, subprocess, re, json

from features.registry import feature, P, TC, FeatureCategory as F


def _netsh(cmd: str) -> str:
    """执行 netsh 命令并返回 stdout"""
    try:
        result = subprocess.run(
            ["netsh"] + cmd.split(),
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        )
        return result.stdout
    except Exception:
        return ""


@feature(
    name="network_status",
    display_name="获取网络状态",
    description="【网络】检测当前网络连接状态、类型（WiFi/以太网）、IP 地址等信息。用于确认网络可用性或诊断连接问题",
    category=F.SYSTEM,
    params=[],
    returns="dict{connected, type, ip, ssid} - 网络状态",
    tags=["network"],
)
def network_status() -> dict:
    result = {"connected": False, "type": None, "ip": None, "ssid": None}
    # 测试外网连接
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3).close()
        result["connected"] = True
    except Exception:
        pass
    # 获取本机 IP
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip and not ip.startswith("127."):
            result["ip"] = ip
    except Exception:
        pass
    # 通过 netsh 获取 WiFi 信息和接口类型
    output = _netsh("wlan show interfaces")
    if "SSID" in output:
        for line in output.splitlines():
            line = line.strip()
            if "SSID" in line and "BSSID" not in line and ":" in line:
                ssid = line.split(":", 1)[1].strip()
                if ssid:
                    result["ssid"] = ssid
                    result["type"] = "wifi"
    # 检查以太网
    if not result["type"]:
        output2 = _netsh("interface show interface")
        if "已连接" in output2 or "Connected" in output2:
            result["type"] = "ethernet"

    return {"success": True, "result": result}


@feature(
    name="wifi_list",
    display_name="列出 WiFi 网络",
    description="【网络】扫描并列出附近可用的 WiFi 网络名称和信号强度。用于选择要连接的网络",
    category=F.SYSTEM,
    params=[],
    returns="list[dict{ssid, signal, security}] - WiFi 列表",
    tags=["network"],
)
def wifi_list() -> dict:
    output = _netsh("wlan show networks mode=bssid")
    networks = []
    current = {}
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("SSID"):
            if current and "ssid" in current:
                networks.append(current)
            current = {"ssid": line.split(":", 1)[1].strip(), "signal": None, "security": None}
        elif "Signal" in line and ":" in line:
            current["signal"] = line.split(":", 1)[1].strip()
        elif "Authentication" in line and ":" in line:
            current["security"] = line.split(":", 1)[1].strip()
    if current and "ssid" in current:
        networks.append(current)
    return {"success": True, "result": networks}


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
    tags=["network"],
)
def wifi_connect(ssid: str, password: str = "") -> dict:
    try:
        if password:
            # 创建临时 WLAN 配置文件
            profile = f'''<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig><SSID><name>{ssid}</name></SSID></SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM><security>
        <authEncryption>
            <authentication>WPA2PSK</authentication>
            <encryption>AES</encryption>
            <useOneX>false</useOneX>
        </authEncryption>
        <sharedKey>
            <keyType>passPhrase</keyType>
            <protected>false</protected>
            <keyMaterial>{password}</keyMaterial>
        </sharedKey>
    </security></MSM>
</WLANProfile>'''
            with open(f"{ssid}.xml", "w", encoding="utf-8") as f:
                f.write(profile)
            _netsh(f"wlan add profile filename=\"{ssid}.xml\"")
            import os
            os.remove(f"{ssid}.xml")

        result = _netsh(f"wlan connect name=\"{ssid}\"")
        success = "已成功完成" in result or "completed successfully" in result.lower()
        return {"success": True, "result": success}
    except Exception as e:
        return {"success": False, "error": f"WiFi 连接失败: {e}"}


@feature(
    name="wifi_disconnect",
    display_name="断开 WiFi",
    description="【网络】断开当前 WiFi 连接。用于切换网络或节省电量",
    category=F.SYSTEM,
    params=[],
    returns="bool - 是否成功",
    tags=["network"],
)
def wifi_disconnect() -> dict:
    try:
        result = _netsh("wlan disconnect")
        success = "已成功完成" in result or "completed successfully" in result.lower()
        return {"success": True, "result": success}
    except Exception as e:
        return {"success": False, "error": str(e)}
