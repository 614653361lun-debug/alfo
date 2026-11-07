import sqlite3
from pathlib import Path


class Database:
    def __init__(self, path=None):
        path = path or Path.home() / "AppData" / "Local" / "IPCameraToolkit" / "devices.db"
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS devices (ip TEXT PRIMARY KEY, mac TEXT, vendor TEXT, kind TEXT, name TEXT, note TEXT, last_seen TEXT)")
        self.conn.commit()

    def save(self, device, seen):
        self.conn.execute("INSERT INTO devices VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(ip) DO UPDATE SET mac=excluded.mac, vendor=excluded.vendor, kind=excluded.kind, last_seen=excluded.last_seen", (device.ip, device.mac, device.vendor, device.kind, device.name, device.note, seen))
        self.conn.commit()

