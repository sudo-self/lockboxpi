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

def get_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def check_usb_devices():
    mtk = "DISCONNECTED"
    usb_active = False
    # Common internal Pi VIDs: Linux Foundation, SMSC, Microchip, VIA
    ignored_vids = ["1d6b", "0424", "2109", "0424", "1a40"] 
    usb_path = "/sys/bus/usb/devices/"
    
    if not os.path.exists(usb_path):
        return mtk, usb_active

    try:
        for device_dir in os.listdir(usb_path):
            if "-" in device_dir and ":" not in device_dir:
                try:
                    with open(os.path.join(usb_path, device_dir, "idVendor"), "r") as f:
                        vid = f.read().strip()
                    if vid == "0e8d":
                        mtk = "CONNECTED"
                        usb_active = True
                    elif vid not in ignored_vids:
                        usb_active = True
                except:
                    continue
    except Exception as e:
        logging.error(f"USB check error: {e}")
    return mtk, usb_active

def get_tunnel_url():
    # Check if cloudflared tunnel service is running
    try:
        result = subprocess.run(["systemctl", "is-active", "cloudflared"], capture_output=True, text=True)
        if result.stdout.strip() == "active":
            return "https://lbpi.jessejesse.com"
    except Exception as e:
        logging.error(f"Failed to check tunnel status: {e}")
    return None

@app.route('/stats')
def get_stats():
    temp_val = "ERR"
    if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                celsius = int(f.read()) / 1000
                fahrenheit = (celsius * 9/5) + 32
                temp_val = str(round(fahrenheit, 1))
        except Exception as e:
            logging.error(f"Failed to read temp: {e}")
    
    ip = get_ip()
    mtk, usb_active = check_usb_devices()
    
    adb = "NONE"
    if usb_active:
        try:
            adb_out = subprocess.check_output(["adb", "devices"], timeout=2).decode().split('\n')
            adb = adb_out[1].split('\t')[0] if len(adb_out) > 1 and adb_out[1].strip() else "NONE"
        except Exception:
            adb = "NONE"

    return jsonify(
        cpu_temp=f"{temp_val}°F",
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
    
    logging.info(f"Executing command: {cmd}")
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=60, cwd=DUMPS_DIR).decode('utf-8')
        logging.info("Command execution successful")
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
    
    # Trigger boot report to Google Doc in the background
    try:
        subprocess.Popen(["python3", "/var/www/report_boot.py"], start_new_session=True)
    except Exception as e:
        logging.error(f"Failed to trigger boot report: {e}")
    
    app.run(host='0.0.0.0', port=5000)