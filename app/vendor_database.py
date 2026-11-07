"""Offline MAC vendor lookup using the bundled IEEE MA-L public listing."""

import csv
from pathlib import Path
import sys

OUI = {
    "001B44": "Hikvision 海康威视",
    "28:57:BE": "Hikvision 海康威视",
    "4C:11:AE": "Dahua 大华",
    "3C:EF:8C": "Dahua 大华",
    "00:09:63": "Cisco",
    "00:1A:A1": "H3C",
    "B0:BE:76": "TP-Link",
    "C8:3A:35": "Huawei 华为",
    "00:E0:4C": "Realtek",
    # Common client/network vendors also seen in home and small-office LANs.
    "84:1B:77": "Intel",
    "C0:95:6D": "Apple 苹果",
    "08:62:66": "ASUS 华硕",
    "5C:A4:F4": "ZTE 中兴",
}
OUI = {prefix.replace(":", "").replace("-", "").upper(): name for prefix, name in OUI.items()}

POPULAR_NAMES = {
    "HIKVISION": "Hikvision 海康威视", "HANGZHOU HIKVISION": "Hikvision 海康威视",
    "DAHUA": "Dahua 大华", "ZHEJIANG DAHUA": "Dahua 大华",
    "UNIVIEW": "Uniview 宇视", "ZHEJIANG UNIVIEW": "Uniview 宇视",
    "TP-LINK": "TP-Link", "HUAWEI": "Huawei 华为", "HUAWEI TECHNOLOGIES": "Huawei 华为",
    "RUIJIE": "Ruijie 锐捷", "NEW H3C": "H3C", "H3C": "H3C",
    "CISCO": "Cisco", "CISCO SYSTEMS": "Cisco", "INTEL": "Intel",
    "APPLE": "Apple 苹果", "ASUSTEK": "ASUS 华硕", "ASUSTEK COMPUTER": "ASUS 华硕",
    "ZTE": "ZTE 中兴", "ZTE CORPORATION": "ZTE 中兴",
}


def _load_ieee_registry():
    """Load the bundled IEEE MA-L, MA-M, and MA-S public assignment lists."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    for filename in ("oui.csv", "mam.csv", "oui36.csv"):
        csv_path = base / "data" / filename
        if not csv_path.exists():
            continue
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    assignment = row.get("Assignment", "").replace("-", "").replace(":", "").strip().upper()
                    company = row.get("Organization Name", "").strip()
                    if len(assignment) in (6, 7, 9) and company:
                        OUI[assignment] = company
        except (OSError, csv.Error):
            continue


_load_ieee_registry()


def normalize(mac):
    return mac.replace("-", ":").upper()


def lookup(mac):
    mac = normalize(mac)
    if not mac or mac == "未知":
        return "未知"
    try:
        first_octet = int(mac[:2], 16)
    except ValueError:
        return "未知"
    # Locally administered MACs include Wi-Fi privacy/randomized client addresses;
    # their apparent prefix is not a trustworthy manufacturer identifier.
    if first_octet & 0x02:
        return "随机 MAC（隐私地址）"
    compact = mac.replace(":", "")
    # Match the longest registered prefix first; local aliases override raw legal names.
    for length in (9, 7, 6):
        key = compact[:length]
        if key in OUI:
            name = OUI[key]
            upper_name = name.upper()
            for alias, friendly in POPULAR_NAMES.items():
                if alias in upper_name:
                    return friendly
            return name
    return "未知"

