import requests
import json
import os
import time
from datetime import datetime

# Configuration
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyHfhHT2nKdQARTNKAHxT2LKTDcGCUc1Z9NgY9MSQX7mbstzREDqbI0zzGv7gxHI2F3/exec"

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
        # Google Apps Script requires a redirect, but we need to ensure the payload follows it.
        # Alternatively, using allow_redirects=True with requests usually handles this, 
        # but GAS sometimes behaves weirdly. Let's send as json but force following.
        response = requests.post(WEB_APP_URL, json=data, allow_redirects=True, timeout=30)
        print(f"Report Status: {response.text}")
    except Exception as e:
        print(f"Failed to send report: {e}")

if __name__ == "__main__":
    # Wait a few seconds for network to be fully ready
    time.sleep(5)
    send_report()
