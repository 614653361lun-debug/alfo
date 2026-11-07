from dataclasses import dataclass
import ipaddress
import re
import socket
import subprocess
import psutil


@dataclass
class AdapterInfo:
    name: str
    ip: str
    netmask: str
    gateway: str = "未知"

    @property
    def network(self):
        return str(ipaddress.ip_network(f"{self.ip}/{self.netmask}", strict=False))


def get_adapters():
    gateways = {}
    try:
        routes = subprocess.check_output(["route", "print", "-4"], text=True, stderr=subprocess.DEVNULL, timeout=3)
        for match in re.finditer(r"(?m)^\s*0\.0\.0\.0\s+0\.0\.0\.0\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\d{1,3}(?:\.\d{1,3}){3})\s+\d+\s*$", routes):
            gateways[match.group(2)] = match.group(1)
    except (OSError, subprocess.SubprocessError):
        pass
    stats = psutil.net_if_stats()
    result = []
    for name, addresses in psutil.net_if_addrs().items():
        for addr in addresses:
            if addr.family == socket.AF_INET and addr.address and not addr.address.startswith("127."):
                if addr.netmask:
                    result.append(AdapterInfo(name, addr.address, addr.netmask, gateways.get(addr.address, "未知")))
    # Virtual and APIPA adapters often appear before the usable Wi-Fi/Ethernet interface.
    result.sort(key=lambda a: (
        a.gateway == "未知",
        a.ip.startswith("169.254."),
        not stats.get(a.name, None) or not stats[a.name].isup,
    ))
    return result


def parse_target(value, fallback):
    value = value.strip()
    if not value:
        return list(ipaddress.ip_network(fallback, strict=False).hosts())
    if "/" in value:
        return list(ipaddress.ip_network(value, strict=False).hosts())
    if "-" in value:
        start, end = [ipaddress.ip_address(x.strip()) for x in value.split("-", 1)]
        return [ipaddress.ip_address(i) for i in range(int(start), int(end) + 1)]
    return [ipaddress.ip_address(value)]

