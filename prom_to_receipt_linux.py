import requests
from escpos.printer import Usb
from datetime import datetime

PROM_URL = "http://prometheus_server:9090"
DEBUG_MODE = True
PRINTER_NAME = "POS-X"  # For reference/logging only
VENDOR_ID = 0x0525  # <-- Replace with actual Vendor ID
PRODUCT_ID = 0xa700  # <-- Replace with actual Product ID

def query(q):
    r = requests.get(f"{PROM_URL}/api/v1/query", params={"query": q})
    r.raise_for_status()
    return r.json()["data"]["result"]

def safe_merge_metric(data, inst, key, value, metric, job_map):
    if inst not in data:
        data[inst] = {
            "type": "unknown",
            "job": metric.get("job") or metric.get("pool") or job_map.get(inst, "unknown")
        }
    data[inst][key] = value

def get_targets_jobmap():
    r = requests.get(f"{PROM_URL}/api/v1/targets")
    r.raise_for_status()
    targets = r.json()["data"]["activeTargets"]
    return {t["discoveredLabels"].get("__address__"): t["labels"].get("job") or t["labels"].get("pool", "unknown") for t in targets}

def get_metrics():
    job_map = get_targets_jobmap()

    # Linux queries
    cpu_node = query('100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)')
    mem_avail = query('node_memory_MemAvailable_bytes')
    mem_total = query('node_memory_MemTotal_bytes')
    uptime = query('node_time_seconds - node_boot_time_seconds')

    # Windows queries
    cpu_win = query('100 - (avg by (instance) (irate(windows_cpu_time_total{mode="idle"}[5m])) * 100)')
    mem_avail_win = query('windows_os_physical_memory_free_bytes')
    mem_total_win = query('windows_cs_physical_memory_bytes')
    uptime_win = query('windows_system_system_up_time')

    data = {}

    for item in cpu_node:
        metric = item['metric']
        inst = metric['instance']
        data[inst] = {
            "cpu": float(item['value'][1]),
            "type": "linux",
            "job": metric.get("job") or metric.get("pool") or job_map.get(inst, "unknown")
        }

    for item in mem_avail:
        safe_merge_metric(data, item["metric"]["instance"], "mem_avail", float(item["value"][1]), item["metric"], job_map)

    for item in mem_total:
        safe_merge_metric(data, item["metric"]["instance"], "mem_total", float(item["value"][1]), item["metric"], job_map)

    for item in uptime:
        safe_merge_metric(data, item["metric"]["instance"], "uptime", float(item["value"][1]) / 3600, item["metric"], job_map)

    # Add Windows results
    for item in cpu_win:
        metric = item['metric']
        inst = metric['instance']
        data[inst] = {
            "cpu": float(item['value'][1]),
            "type": "windows",
            "job": metric.get("job") or metric.get("pool") or job_map.get(inst, "unknown")
        }

    for item in mem_avail_win:
        safe_merge_metric(data, item["metric"]["instance"], "mem_avail", float(item["value"][1]), item["metric"], job_map)

    for item in mem_total_win:
        safe_merge_metric(data, item["metric"]["instance"], "mem_total", float(item["value"][1]), item["metric"], job_map)

    for item in uptime_win:
        safe_merge_metric(data, item["metric"]["instance"], "uptime", float(item["value"][1]) / 3600, item["metric"], job_map)

    return data

def build_output(data):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = [f"METRIC SNAPSHOT\n{now}\n"]

    for inst, values in sorted(data.items()):
        output.append("-" * 32)
        output.append(f"{inst}")
        output.append(f" Job:   {values.get('job', 'unknown')}")
        output.append(f" Type:  {values.get('type', 'unknown')}")
        output.append(f" CPU:   {values.get('cpu', 0):6.1f}%")
        mem_used = int((values.get("mem_total", 0) - values.get("mem_avail", 0)) / 1024 / 1024)
        mem_total = int(values.get("mem_total", 0) / 1024 / 1024)
        output.append(f" RAM:   {mem_used}M / {mem_total}M")
        if "uptime" in values:
            output.append(f" Uptime:{values['uptime']:.1f} hrs")

    output.append("-" * 32)
    return "\n".join(output)

def print_receipt_linux(text):
    try:
        p = Usb(VENDOR_ID, PRODUCT_ID)
        p.set(align='left')
        p.text(text + "\n")
        p._raw(b'\x1B\x64\x05')  # Feed 5 lines
        p.cut()
    except Exception as e:
        print(f"[PRINTER ERROR] {e}")

if __name__ == "__main__":
    data = get_metrics()
    receipt_text = build_output(data)
    print(receipt_text)

    if not DEBUG_MODE:
        print_receipt_linux(receipt_text)
    else:
        print("[DEBUG] Skipping printer output")
