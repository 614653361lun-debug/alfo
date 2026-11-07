from datetime import datetime
import webbrowser
from PySide6.QtCore import QThread
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QProgressBar, QTableWidget, QTableWidgetItem, QSplitter, QListWidget, QFileDialog, QMessageBox,
    QSpinBox, QFormLayout)
from PySide6.QtWidgets import QHeaderView
from .network_info import get_adapters, parse_target
from .scanner import ScannerWorker
from .device_detector import classify, port_text
from .exporter import export_csv


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAN Toolkit · 弱电设备发现与调试工具")
        self.resize(1280, 760)
        self.devices, self.thread, self.worker = [], None, None
        self.adapters = get_adapters()
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #f3f6fa; color: #172b4d; font-family: 'Microsoft YaHei UI'; font-size: 10pt; }
            QLabel { background: transparent; }
            QLineEdit, QComboBox, QSpinBox { background: white; border: 1px solid #d6deea; border-radius: 6px; padding: 8px; min-height: 20px; }
            QPushButton { background: white; border: 1px solid #d6deea; border-radius: 6px; padding: 9px 14px; font-weight: 600; }
            QPushButton:hover { background: #edf4ff; border-color: #83a9e8; }
            QPushButton:disabled { color: #9aa8bc; background: #eef1f5; }
            QPushButton#primary { background: #1769e0; color: white; border: 0; }
            QPushButton#primary:hover { background: #0f57c4; }
            QTableWidget, QListWidget { background: white; border: 1px solid #e0e6ef; border-radius: 8px; gridline-color: #edf1f6; }
            QHeaderView::section { background: #f6f8fb; color: #52647d; border: 0; border-bottom: 1px solid #e0e6ef; padding: 10px; font-weight: 600; }
            QProgressBar { border: 0; border-radius: 4px; background: #e3eaf4; height: 8px; text-align: center; }
            QProgressBar::chunk { background: #1769e0; border-radius: 4px; }
            QSplitter::handle { background: #e6ebf2; width: 5px; }
        """)
        self._build_ui()

    def _build_ui(self):
        root = QWidget(); self.setCentralWidget(root); layout = QVBoxLayout(root)
        top = QHBoxLayout()
        self.adapter = QComboBox(); self.adapter.addItems([f"{a.name} · {a.ip} · 网关 {a.gateway} · {a.network}" for a in self.adapters] or ["未检测到可用网卡"])
        self.target = QLineEdit(); self.target.setPlaceholderText("IP 范围（留空扫描当前网段，如 192.168.1.0/24 或 192.168.1.1-192.168.1.254）")
        self.workers = QSpinBox(); self.workers.setRange(1, 64); self.workers.setValue(16); self.workers.setPrefix("并发 ")
        self.start = QPushButton("开始扫描"); self.start.setObjectName("primary"); self.start.clicked.connect(self.start_scan)
        self.cancel = QPushButton("取消"); self.cancel.setEnabled(False); self.cancel.clicked.connect(self.cancel_scan)
        self.export = QPushButton("导出 CSV"); self.export.clicked.connect(self.export_data)
        for w in (QLabel("网卡"), self.adapter, self.target, self.workers, self.start, self.cancel, self.export): top.addWidget(w)
        layout.addLayout(top)
        self.info = QLabel("就绪 · 默认低负载扫描 · 仅扫描你有权管理的本地网络")
        layout.addWidget(self.info)
        split = QSplitter(); layout.addWidget(split, 1)
        self.filters = QListWidget(); self.filters.addItems(["全部设备", "视频设备", "网络设备", "未知设备"]); self.filters.currentRowChanged.connect(self.filter_rows); split.addWidget(self.filters)
        self.table = QTableWidget(0, 7); self.table.setHorizontalHeaderLabels(["IP 地址", "设备名称", "MAC 厂商", "可能产品", "设备分类", "状态", "置信度"]); self.table.cellClicked.connect(self.show_detail); self.table.setSortingEnabled(True); self.table.setAlternatingRowColors(True); self.table.verticalHeader().setVisible(False); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); split.addWidget(self.table)
        detail = QWidget(); form = QFormLayout(detail); self.detail = QLabel("选择设备查看详情"); self.detail.setWordWrap(True); form.addRow(self.detail)
        self.open_http = QPushButton("打开 HTTP 后台"); self.open_https = QPushButton("打开 HTTPS 后台")
        self.open_http.clicked.connect(lambda: self.open_url("http://")); self.open_https.clicked.connect(lambda: self.open_url("https://"))
        form.addRow(self.open_http, self.open_https); split.addWidget(detail); split.setSizes([140, 700, 360])
        self.progress = QProgressBar(); layout.addWidget(self.progress)

    def selected_adapter(self):
        return self.adapters[self.adapter.currentIndex()] if self.adapters and self.adapter.currentIndex() < len(self.adapters) else None

    def start_scan(self):
        if self.worker: return
        adapter = self.selected_adapter()
        fallback = adapter.network if adapter else "192.168.1.0/24"
        try: targets = parse_target(self.target.text(), fallback)
        except ValueError as exc:
            QMessageBox.warning(self, "范围无效", str(exc)); return
        if len(targets) > 4096:
            QMessageBox.warning(self, "扫描范围过大", f"当前范围包含 {len(targets):,} 个地址，可能导致扫描持续很久。请确认网卡和子网掩码，或输入较小的 CIDR/IP 范围后再扫描。")
            return
        self.devices.clear(); self.table.setRowCount(0); self.progress.setMaximum(len(targets)); self.progress.setValue(0)
        self.thread = QThread(); self.worker = ScannerWorker(targets, self.workers.value()); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run); self.worker.found.connect(self.add_device); self.worker.progress.connect(lambda n, total, ip: self.progress.setValue(n)); self.worker.failed.connect(lambda e: QMessageBox.critical(self, "扫描错误", e)); self.worker.finished.connect(self.scan_finished); self.thread.finished.connect(self.thread.deleteLater)
        self.start.setEnabled(False); self.cancel.setEnabled(True); self.info.setText(f"正在扫描 {len(targets)} 个地址…"); self.thread.start()

    def add_device(self, raw):
        adapter = self.selected_adapter()
        raw["is_gateway"] = bool(adapter and adapter.gateway != "未知" and raw["ip"] == adapter.gateway)
        raw["is_local"] = bool(adapter and raw["ip"] == adapter.ip)
        device = classify(raw); self.devices.append(device); self.add_row(device)

    def add_row(self, d):
        row = self.table.rowCount(); self.table.insertRow(row)
        values = [d.ip, d.name or "未命名", d.vendor, d.product_hint, d.kind, "在线", f"{d.confidence}%"]
        for col, value in enumerate(values): self.table.setItem(row, col, QTableWidgetItem(value))

    def scan_finished(self):
        if self.thread: self.thread.quit(); self.thread.wait(); self.thread = self.worker = None
        self.start.setEnabled(True); self.cancel.setEnabled(False); self.info.setText(f"扫描完成：发现 {len(self.devices)} 台设备。")

    def cancel_scan(self):
        if self.worker: self.worker.cancel(); self.info.setText("正在取消扫描…")

    def show_detail(self, row, _col):
        if row >= len(self.devices): return
        d = self.devices[row]; self.detail.setText(f"IP 地址：{d.ip}\nMAC 地址：{d.mac}\n网卡厂商：{d.vendor}\n设备分类：{d.kind}\n可能产品：{d.product_hint}\n识别置信度：{d.confidence}%\n判断依据：MAC 厂商 + 当前开放端口 + 网关关系；无法确认型号\n开放端口：{port_text(d.ports)}\nONVIF：未检测（后续支持）\nRTSP：{'发现端口，未认证' if 554 in d.ports else '未检测到'}\n最后发现：{datetime.now():%Y-%m-%d %H:%M:%S}")
        self.current = d

    def open_url(self, scheme):
        if hasattr(self, "current"): webbrowser.open(f"{scheme}{self.current.ip}")

    def export_data(self):
        if not self.devices: QMessageBox.information(self, "没有数据", "请先完成一次扫描。"); return
        path, _ = QFileDialog.getSaveFileName(self, "导出 CSV", "scan-result.csv", "CSV 文件 (*.csv)")
        if path: export_csv(path, self.devices); self.info.setText(f"已导出：{path}")

    def filter_rows(self, row):
        selected = self.filters.item(row).text() if row >= 0 else "全部设备"
        for r, d in enumerate(self.devices):
            matches = selected == "全部设备" or selected == d.kind
            if selected == "视频设备": matches = d.kind == "视频设备（待细分）"
            if selected == "网络设备": matches = d.kind == "网络设备（待确认）"
            self.table.setRowHidden(r, not matches)

