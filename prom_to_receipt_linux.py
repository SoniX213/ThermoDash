import requests
import time
from escpos.printer import Usb

PROM_URL = "http://192.168.1.113:9090"
DEBUG_MODE = True
PRINTER_NAME = "POS-X"  # For reference/logging only
VENDOR_ID = 0x0525  # <-- Replace with actual Vendor ID
PRODUCT_ID = 0xa700  # <-- Replace with actual Product ID

def query(expr):
    try:
        resp = requests.get(f"{PROM_URL}/api/v1/query", params={"query": expr})
        return resp.json()["data"]["result"]
    except Exception as e:
        print(f"[QUERY ERROR] {expr}: {e}")
        return []

def get_instance_job_map():
    try:
        resp = requests.get(f"{PROM_URL}/api/v1/targets")
        targets = resp.json()["data"]["activeTargets"]
        return {
            t["labels"].get("instance"): t["labels"].get("job", "unknown")
            for t in targets
            if "instance" in t["labels"]
        }
    except Exception as e:
        print(f"[ERROR] Could not retrieve target map: {e}")
        return {}

def safe_merge_metric(data, inst, key, value, metric, job_map):
    data.setdefault(inst, {})
    data[inst][key] = value
    if 'job' not in data[inst]:
        if 'job' in metric:
            data[inst]['job'] = metric['job']
        elif 'pool' in metric:
            data[inst]['job'] = metric['pool']
        elif inst in job_map:
            data[inst]['job'] = job_map[inst]

def get_metrics():
    data = {}
    job_map = get_instance_job_map()

    cpu_node = query('100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)')
    mem_avail_node = query('node_memory_MemAvailable_bytes')
    mem_total_node = query('node_memory_MemTotal_bytes')
    uptime_node = query('time() - node_boot_time_seconds')

    for item in cpu_node:
        metric = item['metric']
        inst = metric['instance']
        data[inst] = {
            "cpu": float(item['value'][1]),
            "type": "linux",
            "job": metric.get("job") or metric.get("pool") or job_map.get(inst, "unknown")
        }

    for item in mem_avail_node:
        metric = item['metric']
        inst = metric['instance']
        safe_merge_metric(data, inst, "mem_avail", float(item['value'][1]), metric, job_map)

    for item in mem_total_node:
        metric = item['metric']
        inst = metric['instance']
        safe_merge_metric(data, inst, "mem_total", float(item['value'][1]), metric, job_map)

    for item in uptime_node:
        metric = item['metric']
        inst = metric['instance']
        safe_merge_metric(data, inst, "uptime", float(item['value'][1]), metric, job_map)

    return data

def format_receipt(data):
    lines = ["METRIC SNAPSHOT", time.strftime("%Y-%m-%d %H:%M:%S"), "-"*32]
    for inst, metrics in sorted(data.items()):
        lines.append(f"{inst}")
        lines.append(f" Job:   {metrics.get('job', 'unknown')}")
        lines.append(f" Type:  {metrics.get('type','unknown')}")
        lines.append(f" CPU:   {metrics.get('cpu', 0):>5.1f}%")
        if 'mem_total' in metrics and 'mem_avail' in metrics:
            used = metrics['mem_total'] - metrics['mem_avail']
            total = metrics['mem_total']
            lines.append(f" RAM:   {used/1024**2:.0f}M / {total/1024**2:.0f}M")
        if 'uptime' in metrics:
            uptime_hr = metrics['uptime'] / 3600
            lines.append(f" Uptime:{uptime_hr:.1f} hrs")
        lines.append("-"*32)
    return "\n".join(lines)

def print_receipt_linux(text):
    try:
        p = Usb(VENDOR_ID, PRODUCT_ID)
        p.set(align='left')
        p.text(text + "\n")
        p.feed(5)
        p.cut()
    except Exception as e:
        print(f"[PRINTER ERROR] {e}")

if __name__ == "__main__":
    metrics = get_metrics()
    receipt = format_receipt(metrics)
    print(receipt)
    if not DEBUG_MODE:
        print_receipt_linux(receipt)
    else:
        print("[DEBUG] Skipping printer output")
