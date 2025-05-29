# Prometheus Metrics Receipt Printer

🔥 Print live Prometheus system metrics straight to a thermal receipt printer.  
Perfect for homelab dashboards, server racks, nerd flexing, or monitoring with mad style.

---

## 🧠 What It Does

This tool pulls system stats from all Prometheus-exported nodes (both Linux and Windows),
formats them into a clean receipt layout, and prints them to a thermal printer.

---

## 📊 Metrics Collected

- CPU usage (avg over 5m)
- RAM used / total
- Uptime (in hours)
- Job name and instance IP

---

## 🖥 Supported Platforms

- ✅ **Windows**
  - Uses `pywin32` to send raw text to printer
- ✅ **Linux**
  - Uses `python-escpos` and USB vendor/product ID

---

## 🧰 Requirements

### Windows:
```bash
pip install requests pywin32
```
### Linux:
```bash
pip install requests python-escpos
```
