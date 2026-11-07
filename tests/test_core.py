import unittest
from app.network_info import parse_target
from app.device_detector import classify


class CoreTests(unittest.TestCase):
    def test_target_range(self):
        self.assertEqual(len(parse_target("192.168.1.1-192.168.1.3", "192.168.1.0/24")), 3)

    def test_video_device_requires_multiple_signals(self):
        device = classify({"ip": "192.168.1.2", "mac": "00:00:00:00:00:00", "ports": [554]})
        self.assertEqual(device.kind, "未知设备")
        stronger = classify({"ip": "192.168.1.2", "mac": "00:00:00:00:00:00", "ports": [554, 8000]})
        self.assertEqual(stronger.kind, "视频设备（待细分）")

