import csv


def export_csv(path, devices):
    fields = ["IP 地址", "MAC 地址", "MAC 厂商", "可能产品", "设备分类", "置信度", "开放端口"]
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        for d in devices:
            writer.writerow([d.ip, d.mac, d.vendor, d.product_hint, d.kind, f"{d.confidence}%", ", ".join(map(str, d.ports))])

