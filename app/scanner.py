"""Bounded LAN scanner: one small worker pool and one ARP-table read per scan."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import ctypes
import re
import socket
import struct
import subprocess
import threading
from ctypes import wintypes

from PySide6.QtCore import QObject, Signal
from .port_scanner import TCP_PORTS, probe


class ScannerWorker(QObject):
    progress = Signal(int, int, str)
    found = Signal(dict)
    finished = Signal()
    failed = Signal(str)

    def __init__(self, targets, workers=24):
        super().__init__()
        self.targets = targets
        self.workers = max(1, min(workers, 64))
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()

    def _scan_one(self, ip):
        if self.cancel_event.is_set():
            return str(ip), "", []
        ip = str(ip)
        mac = send_arp(ip)
        ports = probe(ip, TCP_PORTS, timeout=0.12, cancel=self.cancel_event)
        return ip, mac, ports

    def run(self):
        total = len(self.targets)
        results = {}
        try:
            # Submit a bounded window instead of queuing an unbounded future per address.
            iterator = iter(self.targets)
            with ThreadPoolExecutor(max_workers=self.workers, thread_name_prefix="lan-probe") as pool:
                pending = {}
                for _ in range(self.workers * 2):
                    ip = next(iterator, None)
                    if ip is None: break
                    pending[pool.submit(self._scan_one, ip)] = ip
                done_count = 0
                while pending and not self.cancel_event.is_set():
                    future = next(as_completed(tuple(pending)))
                    pending.pop(future)
                    ip, mac, ports = future.result()
                    results[ip] = (mac, ports)
                    done_count += 1
                    self.progress.emit(done_count, total, ip)
                    next_ip = next(iterator, None)
                    if next_ip is not None:
                        pending[pool.submit(self._scan_one, next_ip)] = next_ip

            # Windows ARP output is collected once, rather than launching `arp.exe` per IP.
            neighbors = arp_table()
            for ip, (mac, ports) in results.items():
                mac = mac or neighbors.get(ip, "未知")
                if ports or mac != "未知":
                    self.found.emit({"ip": ip, "mac": mac, "ports": ports})
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


def arp_table():
    try:
        output = subprocess.check_output(["arp", "-a"], text=True, stderr=subprocess.DEVNULL, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return {}
    return {
        match.group(1): match.group(2).replace("-", ":").upper()
        for match in re.finditer(r"(?m)^\s*(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-f]{2}(?:[-:][0-9a-f]{2}){5})\s+\w+", output, re.I)
    }


def send_arp(ip):
    """Actively resolve a same-LAN address through Windows IP Helper."""
    if not hasattr(ctypes, "WinDLL"):
        return ""
    try:
        iphlpapi = ctypes.WinDLL("iphlpapi.dll")
        send = iphlpapi.SendARP
        send.argtypes = [wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD)]
        send.restype = wintypes.DWORD
        target = wintypes.DWORD(struct.unpack("=I", socket.inet_aton(ip))[0])
        mac_buffer = (wintypes.DWORD * 2)()
        mac_length = wintypes.DWORD(ctypes.sizeof(mac_buffer))
        if send(target, 0, mac_buffer, ctypes.byref(mac_length)) != 0:
            return ""
        raw = ctypes.string_at(ctypes.byref(mac_buffer), mac_length.value)
        if len(raw) < 6:
            return ""
        return ":".join(f"{byte:02X}" for byte in raw[:6])
    except (OSError, ValueError, struct.error):
        return ""

