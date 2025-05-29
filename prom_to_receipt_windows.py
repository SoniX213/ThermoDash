import requests
import time
import win32print

PROM_URL = "http://prometheus_server:9090"
PRINTER_NAME = "POS-X"
DEBUG_MODE = False  # Set to False to enable actual printing

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

    cpu_win = query('100 - (avg by (instance) (irate(windows_cpu_time_total{mode="idle"}[5m])) * 100)')
    mem_avail_win = query('windows_os_physical_memory_free_bytes')
    mem_total_win = query('windows_cs_physical_memory_bytes')
    uptime_win = query('windows_system_system_up_time')

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

    for item in cpu_win:
        metric = item['metric']
        inst = metric['instance']
        data[inst] = {
            "cpu": float(item['value'][1]),
            "type": "windows",
            "job": metric.get("job") or metric.get("pool") or job_map.get(inst, "unknown")
        }

    for item in mem_avail_win:
        metric = item['metric']
        inst = metric['instance']
        safe_merge_metric(data, inst, "mem_avail", float(item['value'][1]), metric, job_map)

    for item in mem_total_win:
        metric = item['metric']
        inst = metric['instance']
        safe_merge_metric(data, inst, "mem_total", float(item['value'][1]), metric, job_map)

    for item in uptime_win:
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

def print_receipt_windows(text, printer_name=PRINTER_NAME):
    hPrinter = win32print.OpenPrinter(printer_name)
    try:
        hJob = win32print.StartDocPrinter(hPrinter, 1, ("Prometheus Metrics", None, "RAW"))
        win32print.StartPagePrinter(hPrinter)
        feed_and_cut = b'\x1B\x64\x05' + b'\x1D\x56\x00'
        win32print.WritePrinter(hPrinter, text.encode('utf-8') + feed_and_cut)
        win32print.EndPagePrinter(hPrinter)
        win32print.EndDocPrinter(hPrinter)
    finally:
        win32print.ClosePrinter(hPrinter)

if __name__ == "__main__":
    metrics = get_metrics()
    receipt = format_receipt(metrics)
    print(receipt)
    if not DEBUG_MODE:
        print_receipt_windows(receipt)
    else:
        print("[DEBUG] Skipping printer output")
