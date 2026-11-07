from dataclasses import dataclass
from .vendor_database import lookup
from .port_scanner import COMMON_PORTS


@dataclass
class Device:
    ip: str
    mac: str
    vendor: str
    kind: str
    confidence: int
    ports: list
    name: str = ""
    note: str = ""
    online: bool = True
    product_hint: str = "未知设备"


def classify(raw):
    ports = raw.get("ports", [])
    vendor = lookup(raw.get("mac", ""))
    video_signals = sum(port in ports for port in (554, 8000, 37777, 8899))
    if raw.get("is_local"):
        kind, confidence = "本机电脑", 100
        product_hint = "当前运行扫描软件的电脑"
    elif raw.get("is_gateway"):
        kind, confidence = "路由器 / 家庭网关", 95
        product_hint = f"{vendor} 路由器/网关" if vendor != "未知" else "家庭路由器/网关"
    elif 9100 in ports or 631 in ports or 515 in ports:
        kind, confidence = "打印机（可能）", 70
        product_hint = "网络打印机/打印服务设备"
    elif 5000 in ports or 5001 in ports or 2049 in ports:
        kind, confidence = "NAS / 存储设备（可能）", 55
        product_hint = "网络存储或提供文件服务的设备"
    elif video_signals >= 2:
        kind, confidence = "视频设备（待细分）", 72
        product_hint = "摄像机 / NVR / 可视门铃等视频设备（无法细分）"
    elif video_signals == 1:
        kind, confidence = "未知设备", 35
        product_hint = "可能含视频服务；证据不足"
    elif 4370 in ports:
        kind, confidence = "门禁 / 考勤设备（可能）", 65
        product_hint = "可能是门禁控制器或考勤终端；需协议确认"
    elif 161 in ports or (22 in ports and (23 in ports or 80 in ports or 443 in ports)):
        kind, confidence = "网络设备（待确认）", 55
        product_hint = "可能是交换机 / AP / 路由器；SNMP 或页面特征待确认"
    elif 445 in ports or 3389 in ports or (135 in ports and 139 in ports):
        kind, confidence = "电脑 / 文件服务设备（可能）", 55
        product_hint = "可能是 Windows 电脑或文件服务设备"
    elif 80 in ports or 443 in ports:
        kind, confidence = "未知网络设备", 30
        product_hint = "带 Web 服务的网络设备"
    elif vendor == "随机 MAC（隐私地址）":
        kind, confidence = "家庭终端（推测）", 45
        product_hint = "可能是手机 / 平板 / 笔记本（随机 MAC）"
    elif vendor == "Apple 苹果":
        kind, confidence = "Apple 终端", 62
        product_hint = "可能是 iPhone / iPad / Mac，型号未知"
    elif vendor == "Intel":
        kind, confidence = "电脑 / 网络终端（推测）", 55
        product_hint = "Intel 网络接口；整机品牌和类型未知"
    elif vendor == "ASUS 华硕":
        kind, confidence = "ASUS 设备（待确认）", 50
        product_hint = "华硕网卡/设备；具体产品未知"
    else:
        kind, confidence = "未知设备", 20
        product_hint = "无法从现有网络特征判断"
    return Device(raw["ip"], raw.get("mac", "未知"), vendor, kind, min(confidence, 99), ports, product_hint=product_hint)


def port_text(ports):
    return ", ".join(f"{p}/{COMMON_PORTS.get(p, 'TCP')}" for p in ports) or "未知"

