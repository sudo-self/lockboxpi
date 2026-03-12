import urllib.request
import urllib.parse
import json
import os
import time
import ssl
from datetime import datetime

# Configuration
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyTaEZV9j6U-gYIi7kOwP-oGm6ZVzNB5l6DEFxdI1B3XDIlRwPCiTXxXKT7k1dA0XUu/exec"

def get_stats():
    # Get Temp in F
    temp_f = "N/A"
    if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                celsius = int(f.read()) / 1000
                temp_f = f"{round((celsius * 9/5) + 32, 1)}F"
        except: pass

    # Get Tunnel URL
    tunnel_url = "N/A"
    try:
        # Give cloudflared a moment to establish the tunnel if this runs early
        for _ in range(10):
            if os.path.exists("/tmp/cloudflared.log"):
                with open("/tmp/cloudflared.log", "r") as f:
                    for line in f:
                        if "trycloudflare.com" in line:
                            parts = line.split("https://")
                            if len(parts) > 1:
                                tunnel_url = "https://" + parts[1].split()[0].replace("|", "").strip()
                                break
            if tunnel_url != "N/A": break
            time.sleep(2)
    except: pass

    return {
        "service": "lockboxpi.local",
        "temp": temp_f,
        "time": datetime.now().strftime("%H%M"),
        "tunnel": tunnel_url
    }

def send_report():
    data = get_stats()
    try:
        req = urllib.request.Request(WEB_APP_URL)
        req.add_header('Content-Type', 'application/json')
        jsondata = json.dumps(data).encode('utf-8')
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, jsondata, timeout=30, context=ctx) as response:
            print(f"Report Status: {response.read().decode('utf-8')}")
    except Exception as e:
        print(f"Failed to send report: {e}")

if __name__ == "__main__":
    # Wait a few seconds for network to be fully ready
    time.sleep(5)
    send_report()
