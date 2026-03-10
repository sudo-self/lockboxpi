from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import subprocess

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Centralized Paths
MTK_PYTHON = "/home/lockboxpi/mtk_env/bin/python3"
MTK_SCRIPT = "/home/lockboxpi/mtkclient/mtk.py"
KNIFE_SCRIPT = "/home/lockboxpi/LockKnife/LockKnife.sh"
DUMPS_DIR = "/var/www/dumps"
WIFI_DB = "/var/lib/dietpi/dietpi-wifi.db"

def get_storage_free():
    try:
        st = os.statvfs('/')
        free = (st.f_bavail * st.f_frsize) / (1024**3)
        return f"{round(free, 1)}GB"
    except: return "0GB"

def get_uptime():
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.readline().split()[0])
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    except: return "0h 0m"

@app.route('/stats')
def get_stats():
    temp_val = "ERR"
    if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_val = str(round(int(f.read()) / 1000, 1))
        except: pass
    
    try:
        ip = subprocess.check_output(["hostname", "-I"]).decode().split()[0]
    except: ip = "127.0.0.1"

    try:
        adb_out = subprocess.check_output(["adb", "devices"]).decode().split('\n')
        adb = adb_out[1].split('\t')[0] if len(adb_out) > 1 and adb_out[1].strip() else "NONE"
    except: adb = "NONE"

    try:
        lsusb = subprocess.check_output(["lsusb"]).decode()
        mtk = "CONNECTED" if "0e8d" in lsusb else "DISCONNECTED"
        # Check for external devices by ignoring internal Pi USB controllers/hubs
        ignored = ["Linux Foundation", "VIA Labs, Inc. Hub", "Standard Microsystems Corp.", "Microchip Technology, Inc."]
        usb_active = any(not any(ign in line for ign in ignored) and line.strip() for line in lsusb.split('\n'))
    except: 
        mtk = "ERR"
        usb_active = False

    return jsonify(
        cpu_temp=f"{temp_val}°C",
        storage_free=get_storage_free(),
        uptime=get_uptime(),
        device=adb,
        mtk_status=mtk,
        ip_address=ip,
        usb_active=usb_active
    )

@app.route('/terminal/run', methods=['POST'])
def run_custom_command():
    cmd = request.json.get("command", "")
    if cmd.startswith("mtk "):
        cmd = cmd.replace("mtk ", f"{MTK_PYTHON} {MTK_SCRIPT} ")
    elif cmd.startswith("knife "):
        cmd = cmd.replace("knife ", f"sudo {KNIFE_SCRIPT} ")
    
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=60, cwd=DUMPS_DIR).decode('utf-8')
        return jsonify(status="success", output=output if output.strip() else "Command executed (No Output)")
    except Exception as e:
        err = e.output.decode() if hasattr(e, 'output') else str(e)
        return jsonify(status="error", output=err)

@app.route('/wifi/connect', methods=['POST'])
def wifi_connect():
    data = request.json
    ssid, psk, slot = data.get("ssid"), data.get("psk"), data.get("slot", 3)
    try:
        subprocess.run(f"sudo sed -i \"s/^aWIFI_SSID\[{slot}\]=.*/aWIFI_SSID\[{slot}\]='{ssid}'/\" {WIFI_DB}", shell=True, check=True)
        subprocess.run(f"sudo sed -i \"s/^aWIFI_PASSWORD\[{slot}\]=.*/aWIFI_PASSWORD\[{slot}\]='{psk}'/\" {WIFI_DB}", shell=True, check=True)
        subprocess.run(f"sudo sed -i \"s/^aWIFI_KEYMGR\[{slot}\]=.*/aWIFI_KEYMGR\[{slot}\]='WPA-PSK'/\" {WIFI_DB}", shell=True, check=True)
        subprocess.run("sudo /boot/dietpi/func/dietpi-wifidb 1", shell=True, check=True)
        subprocess.Popen("sleep 5 && sudo reboot", shell=True)
        return jsonify(status="success", output=f"Slot {slot} updated. Rebooting...")
    except Exception as e:
        return jsonify(status="error", output=str(e))

@app.route('/mtk/<cmd>')
def run_mtk_action(cmd):
    try:
        full_cmd = f"{MTK_PYTHON} {MTK_SCRIPT} {cmd}"
        output = subprocess.check_output(full_cmd, shell=True, stderr=subprocess.STDOUT, timeout=60, cwd=DUMPS_DIR).decode('utf-8')
        return jsonify(status="success", output=output)
    except Exception as e:
        err = e.output.decode() if hasattr(e, 'output') else str(e)
        return jsonify(status="error", output=err)

@app.route('/lk/<cmd>')
def run_lk_action(cmd):
    flag = "--pull-pattern" if cmd == "pull-pattern" else "--dump-system"
    try:
        output = subprocess.check_output(f"sudo {KNIFE_SCRIPT} {flag}", shell=True, stderr=subprocess.STDOUT, timeout=300, cwd=DUMPS_DIR).decode('utf-8')
        return jsonify(status="success", output=output)
    except Exception as e:
        err = e.output.decode() if hasattr(e, 'output') else str(e)
        return jsonify(status="error", output=err)

if __name__ == '__main__':
    # Apply touch orientation matrix for 3.5" TFT on startup
    try:
        # Inverted X and Inverted Y (180 degree rotation)
        matrix = "-1 0 1 0 -1 1 0 0 1" 
        subprocess.run(f"DISPLAY=:0 xinput set-prop 'ADS7846 Touchscreen' 'Coordinate Transformation Matrix' {matrix}", shell=True)
    except Exception as e:
        print(f"Touch Calibration Failed: {e}")
    
    app.run(host='0.0.0.0', port=5000)
