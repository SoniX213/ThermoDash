# ThermoDash 🧾🔥

**Print Prometheus metrics on a thermal receipt printer in real time.**  
Perfect for homelabs, rack dashboards, monitoring kiosks, or just flexing.

---

## 📊 What It Prints

- CPU usage (5-minute avg)
- RAM usage
- System uptime
- Instance IP and Prometheus job name

Supports both **Linux** and **Windows** exporters.

---

## 🖥 Supported Platforms

- ✅ **Windows** (raw USB via `pywin32`)
- ✅ **Linux** (ESC/POS USB via `python-escpos`)

---

## 🧰 Requirements

### 🔧 Windows:
```bash
pip install requests pywin32
```
### 🐧 Linux:
```bash
pip install requests python-escpos
```
📦 File Structure
File	Purpose
prom_to_receipt_win.py	Windows printer version (raw text)
prom_to_receipt_linux.py	Linux printer version (USB via ESC/POS)
README.md	You're reading it
LICENSE	MIT licensed, free for all

🔧 Configuration
```
Inside either script, set the following at the top:

PROM_URL = "http://prometheus_server:9090"  # Your Prometheus endpoint
DEBUG_MODE = True                      # Disable printing while testing
PRINTER_NAME = "POS-X"                 # (Windows only)
VENDOR_ID = 0x04b8                     # (Linux) Replace with your actual ID
PRODUCT_ID = 0x0202                    # (Linux) Replace with your actual ID
```
To find your USB printer's vendor/product ID on Linux:

lsusb

Example:
```bash
Bus 001 Device 004: ID 04b8:0202 Seiko Epson Corp. Receipt Printer
```
🐧 Linux: udev Rules

To allow printing without root:

 Create this file:
```
sudo nano /etc/udev/rules.d/99-thermodash-printer.rules
```
 Add this rule:
```
SUBSYSTEM=="usb", ATTRS{idVendor}=="04b8", ATTRS{idProduct}=="0202", MODE="0666"
```
 Reload and apply:
```
sudo udevadm control --reload-rules
sudo udevadm trigger
```
🖨 Sample Output
```
METRIC SNAPSHOT
2025-05-29 10:13:33
--------------------------------
192.168.1.249:9100
 Job:   PVH2
 Type:  linux
 CPU:   32.7%
 RAM:   15057M / 15857M
 Uptime:237.4 hrs
--------------------------------
192.168.1.250:9182
 Job:   PVH-Win
 Type:  windows
 CPU:   14.1%
 RAM:   8085M / 16237M
--------------------------------
```
🧠 Future Ideas

Group output by job type

Threshold warnings (⚠️ CPU > 90%)

Auto-run via cron or systemd timer

Print Grafana dashboard QR on footer

