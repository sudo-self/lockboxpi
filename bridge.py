from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import subprocess
import logging
import serial
import time

# Configure basic logging for reliability and debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Centralized Paths
MTK_PYTHON = "/home/lockboxpi/mtk_env/bin/python3"
MTK_SCRIPT = "/home/lockboxpi/mtkclient/mtk.py"
KNIFE_SCRIPT = "/home/lockboxpi/LockKnife/LockKnife.sh"
DUMPS_DIR = "/home/lockboxpi/dumps"
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

def check_serial_devices():
    import glob
    ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
    return "CONNECTED" if ports else "DISCONNECTED"

def is_process_running(name):
    try:
        for p in os.listdir('/proc'):
            if p.isdigit():
                try:
                    with open(os.path.join('/proc', p, 'comm'), 'r') as f:
                        if name in f.read():
                            return True
                except:
                    continue
    except Exception as e:
        logging.error(f"Failed process check: {e}")
    return False

def get_tunnel_url():
    # Fast check without forking a subprocess
    if is_process_running("cloudflared"):
        return "https://lbpi.jessejesse.com"
    return None

@app.route('/tunnel/toggle', methods=['POST'])
def toggle_tunnel():
    try:
        # Check if running to toggle it
        result = subprocess.run(["systemctl", "is-active", "cloudflared"], capture_output=True, text=True)
        if result.stdout.strip() == "active":
            subprocess.run(["sudo", "systemctl", "stop", "cloudflared"], check=True)
            return jsonify(status="success", output="Cloudflare tunnel STOPPED.")
        else:
            subprocess.run(["sudo", "systemctl", "start", "cloudflared"], check=True)
            return jsonify(status="success", output="Cloudflare tunnel STARTED.")
    except Exception as e:
        return jsonify(status="error", output=f"Failed to toggle tunnel service: {str(e)}")

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
    serial_status = check_serial_devices()
    
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
        serial_status=serial_status,
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

class ObsidianFRP:
    def __init__(self, serial_port=None, baudrate=115200):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.ser = None
        self.logs = []

    def log(self, message, msg_type='INFO'):
        timestamp = time.strftime('%H:%M:%S')
        log_msg = f"[{timestamp}] [{msg_type}] {message}"
        self.logs.append(log_msg)
        logging.info(log_msg)

    def connect_serial(self):
        try:
            self.ser = serial.Serial(self.serial_port, self.baudrate, timeout=1)
            self.log(f"SERIAL PORT {self.serial_port} OPENED")
            return True
        except Exception as e:
            self.log(f"SERIAL ERROR: {e}", "ERROR")
            return False

    def disconnect_serial(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.log("SERIAL DISCONNECTED")

    def send_at_command(self, command):
        if not self.ser or not self.ser.is_open:
            self.log("ERROR: NO ACTIVE SERIAL SESSION", "ERROR")
            return
        try:
            if not command.endswith('\r\n'):
                command += '\r\n'
            self.log(command.strip(), "CMD")
            self.ser.write(command.encode())
            time.sleep(0.5)
            response = self.ser.read_all().decode(errors='ignore')
            if response:
                for line in response.splitlines():
                    if line.strip():
                        self.log(f"RECV >> {line.strip()}")
        except Exception as e:
            self.log(f"SEND ERROR: {e}", "ERROR")

    def send_adb_command(self, command):
        try:
            self.log(f"SHELL >> {command}", "CMD")
            cmd_list = ['adb', 'shell'] + command.split()
            result = subprocess.run(cmd_list, capture_output=True, text=True)
            if result.returncode == 0:
                self.log("EXECUTION SUCCESS")
                if result.stdout:
                    self.log(result.stdout.strip())
            else:
                self.log(f"EXECUTION FAILED: {result.stderr.strip()}", "ERROR")
        except Exception as e:
            self.log(f"ADB ERROR: {e}", "ERROR")

    def init_adb_handshake(self):
        try:
            self.log("INITIALIZING ADB HANDSHAKE...")
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            if result.returncode == 0:
                self.log("ADB BRIDGE ESTABLISHED")
                self.log(result.stdout.strip())
            else:
                self.log("ADB ERROR: Ensure adb is installed and device is connected", "ERROR")
        except Exception as e:
            self.log(f"ADB INIT ERROR: {e}", "ERROR")

@app.route('/obsidian/samsung-frp')
def run_obsidian_frp():
    import glob
    ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
    serial_port = ports[0] if ports else '/dev/ttyACM0'

    frp = ObsidianFRP(serial_port=serial_port, baudrate=115200)
    
    # Interface 01: Serial AT Bridge
    if frp.connect_serial():
        frp.send_at_command('AT+KSTRINGB=0,3')
        frp.send_at_command('AT+DUMPCTRL=1,0')
        frp.send_at_command('AT+DEBUGLVC=0,5')
        frp.send_at_command('AT+SWATD=0')
        frp.send_at_command('AT+ACTIVATE=0,0,0')
        frp.send_at_command('AT+SWATD=1')
        frp.disconnect_serial()
    else:
        frp.log("COULD NOT OPEN SERIAL AT INTERFACE. CONTINUING TO ADB FALLBACK.", "WARN")

    # Interface 02: USB ADB Bridge
    frp.init_adb_handshake()
    frp.send_adb_command('settings put global setup_wizard_has_run 1')
    frp.send_adb_command('settings put secure user_setup_complete 1')
    frp.send_adb_command('content insert --uri content://settings/secure --bind name:s:DEVICE_PROVISIONED --bind value:i:1')
    frp.send_adb_command('content insert --uri content://settings/secure --bind name:s:user_setup_complete --bind value:i:1')
    frp.send_adb_command('am start -c android.intent.category.HOME -a android.intent.action.MAIN')
    
    return jsonify(status="success", output="\n".join(frp.logs))

if __name__ == '__main__':
    # Trigger boot report to Google Doc in the background
    try:
        subprocess.Popen(["python3", "/home/lockboxpi/report_boot.py"], start_new_session=True)
    except Exception as e:
        logging.error(f"Failed to trigger boot report: {e}")
    
    app.run(host='0.0.0.0', port=5000)