import socket
from concurrent.futures import ThreadPoolExecutor

COMMON_PORTS = {
    80: "HTTP", 443: "HTTPS", 554: "RTSP", 8000: "Hikvision SDK", 37777: "Dahua SDK",
    8899: "ONVIF", 161: "SNMP", 22: "SSH", 23: "Telnet", 3389: "RDP", 9100: "打印服务",
    8080: "备用 HTTP", 8443: "备用 HTTPS", 4370: "门禁/考勤服务（常见端口）",
    5000: "NAS/应用服务", 5001: "NAS HTTPS", 445: "Windows 文件共享",
    139: "NetBIOS", 135: "Windows RPC", 631: "IPP 打印", 515: "LPD 打印",
    2049: "NFS", 3702: "WS-Discovery", 5357: "设备发现服务",
}

# UDP-only discovery services are kept in the label map but excluded from TCP connect checks.
TCP_PORTS = tuple(port for port in COMMON_PORTS if port not in (161, 3702))


def probe(ip, ports, timeout=0.25, workers=32, cancel=None):
    def check(port):
        if cancel and cancel.is_set():
            return None
        try:
            with socket.create_connection((str(ip), port), timeout=timeout):
                return port
        except (OSError, TimeoutError):
            return None
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return sorted(p for p in pool.map(check, ports) if p)

