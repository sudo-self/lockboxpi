from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import subprocess
import logging

# Configure basic logging for reliability and debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    except Exception as e:
        logging.error(f"Failed to get storage free: {e}")
        return "0GB"

def get_uptime():
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.readline().split()[0])
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    except Exception as e:
        logging.error(f"Failed to get uptime: {e}")
        return "0h 0m"

def get_tunnel_url():
    try:
        if os.path.exists("/tmp/cloudflared.log"):
            with open("/tmp/cloudflared.log", "r") as f:
                for line in f:
                    if "trycloudflare.com" in line:
                        parts = line.split("https://")
                        if len(parts) > 1:
                            url = "https://" + parts[1].split()[0].replace("|", "").strip()
                            return url
    except Exception as e:
        logging.error(f"Failed to get tunnel URL: {e}")
    return None

@app.route('/stats')
def get_stats():
    temp_val = "ERR"
    if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_val = str(round(int(f.read()) / 1000, 1))
        except Exception as e:
            logging.error(f"Failed to read temp: {e}")
    
    try:
        ip_out = subprocess.check_output(["hostname", "-I"], timeout=5).decode().strip()
        ip = ip_out.split()[0] if ip_out else "lockboxpi.local"
    except Exception as e:
        ip = "lockboxpi.local"

    try:
        adb_out = subprocess.check_output(["adb", "devices"], timeout=5).decode().split('\n')
        adb = adb_out[1].split('\t')[0] if len(adb_out) > 1 and adb_out[1].strip() else "NONE"
    except Exception as e:
        logging.error(f"Failed to get ADB devices: {e}")
        adb = "NONE"

    try:
        lsusb = subprocess.check_output(["lsusb"], timeout=5).decode()
        mtk = "CONNECTED" if "0e8d" in lsusb else "DISCONNECTED"
        
        # Strictly ignore internal Pi components and generic hubs to detect target devices
        ignored_patterns = [
            "Linux Foundation", 
            "VIA Labs, Inc. Hub", 
            "Standard Microsystems Corp.", 
            "Microchip Technology, Inc.",
            "root hub",
            "hub"
        ]
        
        # Check if any line in lsusb represents a device that isn't on the ignore list
        usb_active = False
        for line in lsusb.split('\n'):
            line = line.strip()
            if not line: continue
            if not any(pattern.lower() in line.lower() for pattern in ignored_patterns):
                usb_active = True
                break
        
        # Also force active if specialized forensic modes are detected
        if adb != "NONE" or mtk == "CONNECTED":
            usb_active = True
            
    except Exception as e:
        logging.error(f"Failed to get lsusb: {e}")
        mtk = "ERR"
        usb_active = False

    return jsonify(
        cpu_temp=f"{temp_val}°C",
        storage_free=get_storage_free(),
        uptime=get_uptime(),
        device=adb,
        mtk_status=mtk,
        ip_address=ip,
        usb_active=usb_active,
        tunnel_url=get_tunnel_url()
    )

@app.route('/terminal/run', methods=['POST'])
def run_custom_command():
    cmd = request.json.get("command", "")
    if not cmd:
        return jsonify(status="error", output="Empty command provided")

    if cmd.startswith("mtk "):
        cmd = cmd.replace("mtk ", f"sudo {MTK_PYTHON} {MTK_SCRIPT} ", 1)
    elif cmd.startswith("knife "):
        cmd = cmd.replace("knife ", f"sudo {KNIFE_SCRIPT} ", 1)
    
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=60, cwd=DUMPS_DIR).decode('utf-8')
        return jsonify(status="success", output=output if output.strip() else "Command executed (No Output)")
    except subprocess.TimeoutExpired:
        return jsonify(status="error", output="Command timed out after 60 seconds")
    except subprocess.CalledProcessError as e:
        err = e.output.decode('utf-8', errors='replace') if e.output else "Command failed with non-zero exit status"
        return jsonify(status="error", output=err)
    except Exception as e:
        return jsonify(status="error", output=str(e))

@app.route('/wifi/connect', methods=['POST'])
def wifi_connect():
    data = request.json
    if not data:
        return jsonify(status="error", output="No data provided")
        
    ssid = data.get("ssid")
    psk = data.get("psk")
    slot = data.get("slot", 3)
    
    if not ssid or not psk:
         return jsonify(status="error", output="Missing SSID or Password")

    try:
        # Avoid basic shell injection in sed by escaping single quotes
        def escape_sh(s):
            return str(s).replace("'", "'\"'\"'")
            
        safe_ssid = escape_sh(ssid)
        safe_psk = escape_sh(psk)
        safe_slot = escape_sh(slot)

        subprocess.run(f"sudo sed -i \"s/^aWIFI_SSID\\[{safe_slot}\\]=.*/aWIFI_SSID\\[{safe_slot}\\]='{safe_ssid}'/\" {WIFI_DB}", shell=True, check=True)
        subprocess.run(f"sudo sed -i \"s/^aWIFI_PASSWORD\\[{safe_slot}\\]=.*/aWIFI_PASSWORD\\[{safe_slot}\\]='{safe_psk}'/\" {WIFI_DB}", shell=True, check=True)
        subprocess.run(f"sudo sed -i \"s/^aWIFI_KEYMGR\\[{safe_slot}\\]=.*/aWIFI_KEYMGR\\[{safe_slot}\\]='WPA-PSK'/\" {WIFI_DB}", shell=True, check=True)
        subprocess.run("sudo /boot/dietpi/func/dietpi-wifidb 1", shell=True, check=True)
        subprocess.Popen("sleep 5 && sudo reboot", shell=True)
        return jsonify(status="success", output=f"Slot {safe_slot} updated. Rebooting...")
    except subprocess.CalledProcessError as e:
        logging.error(f"WiFi configuration failed: {e}")
        return jsonify(status="error", output=f"WiFi configuration command failed")
    except Exception as e:
        return jsonify(status="error", output=str(e))

@app.route('/mtk/<cmd>')
def run_mtk_action(cmd):
    try:
        full_cmd = f"sudo {MTK_PYTHON} {MTK_SCRIPT} {cmd}"
        output = subprocess.check_output(full_cmd, shell=True, stderr=subprocess.STDOUT, timeout=60, cwd=DUMPS_DIR).decode('utf-8')
        return jsonify(status="success", output=output)
    except subprocess.TimeoutExpired:
        return jsonify(status="error", output="MTK command timed out after 60 seconds")
    except subprocess.CalledProcessError as e:
        err = e.output.decode('utf-8', errors='replace') if e.output else "MTK command failed"
        return jsonify(status="error", output=err)
    except Exception as e:
        return jsonify(status="error", output=str(e))

@app.route('/lk/<cmd>')
def run_lk_action(cmd):
    try:
        output = ""
        if cmd == "pull-pattern":
            # Direct ADB commands to bypass the broken LockKnife v3.5.0 CLI
            cmds = [
                "adb shell su -c 'cp /data/system/gesture.key /sdcard/ && cp /data/system/password.key /sdcard/ && cp /data/system/gatekeeper.password.key /sdcard/'",
                "adb pull /sdcard/gesture.key ./",
                "adb pull /sdcard/password.key ./",
                "adb pull /sdcard/gatekeeper.password.key ./"
            ]
            for c in cmds:
                try:
                    res = subprocess.check_output(c, shell=True, stderr=subprocess.STDOUT, timeout=10, cwd=DUMPS_DIR).decode('utf-8')
                    output += res + "\n"
                except subprocess.CalledProcessError as e:
                    output += f"Failed: {c}\n"
            if not output.strip():
                output = "Executed pattern pull commands. Check dumps folder."
        elif cmd == "dump-system":
            output = subprocess.check_output("adb pull /system ./system_dump", shell=True, stderr=subprocess.STDOUT, timeout=300, cwd=DUMPS_DIR).decode('utf-8')
        else:
            output = f"Unknown KNIFE command: {cmd}"

        return jsonify(status="success", output=output)
    except subprocess.TimeoutExpired:
        return jsonify(status="error", output="Command timed out.")
    except subprocess.CalledProcessError as e:
        err = e.output.decode('utf-8', errors='replace') if e.output else "Command failed"
        return jsonify(status="error", output=err)
    except Exception as e:
        return jsonify(status="error", output=str(e))

if __name__ == '__main__':
    # Apply touch orientation matrix for 3.5" TFT on startup
    try:
        # Calibrated Matrix for 3.5" TFT
        matrix = "1.1 0 -0.05 0 1.1 -0.05 0 0 1" 
        subprocess.run(f"DISPLAY=:0 xinput set-prop 'ADS7846 Touchscreen' 'Coordinate Transformation Matrix' {matrix}", shell=True, check=True)
        logging.info("Touch calibration applied successfully.")
    except Exception as e:
        logging.error(f"Touch Calibration Failed: {e}")
    
    app.run(host='0.0.0.0', port=5000)