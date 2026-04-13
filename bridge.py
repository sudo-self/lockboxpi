from flask import Flask, jsonify, request, send_from_directory, redirect
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import subprocess
import logging
import serial
import time
import glob
import threading
import re

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
# CORS ensures your browser/TFT doesn't block the "Offline" bridge
CORS(app, resources={r"/api/*": {"origins": "*"}})

# --- PATH CONFIGURATION ---
MTK_PYTHON = "/home/lockboxpi/mtk_env/bin/python3"
MTK_SCRIPT = "/home/lockboxpi/mtkclient/mtk.py"
KNIFE_SCRIPT = "/home/lockboxpi/LockKnife/LockKnife.sh"
DUMPS_DIR = "/home/lockboxpi/dumps"
WIFI_DB = "/var/lib/dietpi/dietpi-wifi.db"
ALT_SERVER_DIR = "/home/lockboxpi/alt-server"
ADB_BINARY = "/usr/bin/adb"
ENV_PATH = "/home/lockboxpi/.env"
BASH_ENGINE = "/home/lockboxpi/p_enroll.sh"

# Ensure directory exists
os.makedirs(DUMPS_DIR, exist_ok=True)

# --- 1. ROOT ROUTE (Serves your index.html) ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/android')
def android_page():
    return send_from_directory('.', 'android.html')

# --- 2. UPLOAD PORTAL (The Mobile-Friendly Dropzone) ---
@app.route('/upload')
def dropzone_page():
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            :root {{
                --base-crust: #0f1012; --plate-surface: #1a1c20; --plate-highlight: #282a2f;
                --accent-core: #ff9d00; --text-primary: #e2e4e9; --text-dim: #5d626f; --safe-core: #00ffa2;
            }}
            body {{ background: var(--base-crust); color: var(--text-primary); font-family: 'Inter', sans-serif; margin: 0; padding: 15px; text-align: center; }}
            #drop-area {{
                border: 2px dashed var(--plate-highlight); border-radius: 12px; padding: 60px 20px;
                background: var(--plate-surface); color: var(--accent-core); font-family: 'JetBrains Mono';
                font-weight: bold; transition: 0.2s; cursor: pointer; margin-top: 20px;
            }}
            #drop-area.highlight {{ border-color: var(--accent-core); background: #1f2126; }}
            .nav-box {{ margin-top: 30px; display: flex; justify-content: center; gap: 10px; }}
            .btn {{ color: var(--text-dim); text-decoration: none; font-size: 11px; border: 1px solid var(--plate-highlight); padding: 10px 15px; border-radius: 4px; font-weight: 900; text-transform: uppercase; }}
            #status {{ margin-top: 20px; font-family: 'JetBrains Mono'; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div style="font-size:10px; font-family:'JetBrains Mono'; color:var(--text-dim);">FIELD_INTAKE // <span style="color:var(--accent-core);">DROPZONE</span></div>
        <div id="drop-area">📦 TAP TO UPLOAD<br><span style="font-size:10px; opacity:0.6;">OR DRAG FILES</span></div>
        <input type="file" id="fileElem" multiple style="display:none" onchange="handleFiles(this.files)">
        <div id="status">STATUS: READY</div>
        <div class="nav-box">
            <a href="/" class="btn">DASHBOARD</a>
            <a href="/dumps/" class="btn" style="border-color: var(--accent-core); color: var(--accent-core);">VAULT</a>
        </div>
        <script>
            let dz = document.getElementById('drop-area');
            let st = document.getElementById('status');
            dz.onclick = () => document.getElementById('fileElem').click();
            async function handleFiles(files) {{
                st.innerText = "UPLOADING..."; st.style.color = "var(--accent-core)";
                for (let file of files) {{
                    let fd = new FormData();
                    fd.append('file', file);
                    await fetch('/api/upload', {{ method: 'POST', body: fd }});
                }}
                st.innerText = "DONE. SAVED TO VAULT."; st.style.color = "var(--safe-core)";
                setTimeout(() => {{ st.innerText = "STATUS: READY"; st.style.color = "var(--text-primary)"; }}, 3000);
            }}
        </script>
    </body>
    </html>
    """

# --- 3. UPLOAD/FILE HANDLING API ---
@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: return jsonify(status="error"), 400
    file = request.files['file']
    if file.filename == '': return jsonify(status="error"), 400
    filename = secure_filename(file.filename)
    file.save(os.path.join(DUMPS_DIR, filename))
    return jsonify(status="success")

# --- 4. DUMPS/VAULT ROUTE (Browsing) ---
@app.route('/dumps/')
@app.route('/dumps/<path:filename>')
def serve_dumps(filename=None):
    if filename:
        return send_from_directory(DUMPS_DIR, filename)
    
    try:
        files = sorted(os.listdir(DUMPS_DIR))
        rows = ""
        for f in files:
            file_path = os.path.join(DUMPS_DIR, f)
            stats = os.stat(file_path)
            size = f"{round(stats.st_size / 1024, 1)} KB"
            mtime = time.strftime('%y-%m-%d %H:%M', time.localtime(stats.st_mtime))
            
            rows += f"""
            <tr>
                <td><a href="/dumps/{f}">{f}</a></td>
                <td style="color:var(--text-dim); font-family:'JetBrains Mono';">{mtime}</td>
                <td style="color:var(--text-dim); font-family:'JetBrains Mono';">{size}</td>
                <td style="text-align:right;"><button onclick="purgeFile('{f}')" style="background:none; border:none; color:#ff4444; font-family:'JetBrains Mono'; cursor:pointer; font-weight:bold;">[X]</button></td>
            </tr>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                :root {{
                    --base-crust: #0f1012; --plate-surface: #1a1c20; --plate-highlight: #282a2f;
                    --plate-shadow: #08090a; --accent-core: #ff9d00; --text-primary: #e2e4e9;
                    --text-dim: #5d626f; --bevel-outer: 2px 2px 5px var(--plate-shadow), -1px -1px 3px var(--plate-highlight);
                }}
                body {{ background-color: var(--base-crust); color: var(--text-primary); font-family: 'Inter', sans-serif; margin: 0; padding: 8px; }}
                .tectonic-nav {{
                    background: var(--plate-surface); padding: 12px; border-radius: 8px;
                    box-shadow: var(--bevel-outer); border: 1px solid var(--plate-highlight);
                    display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px;
                }}
                .repo-label {{ font-family: 'JetBrains Mono'; font-size: 10px; font-weight: 700; color: var(--text-dim); text-transform: uppercase; }}
                .repo-label span {{ color: var(--accent-core); }}
                .back-btn {{
                    background: var(--plate-surface); box-shadow: var(--bevel-outer); color: var(--text-primary);
                    text-decoration: none; font-family: 'Inter'; font-weight: 900; font-size: 10px;
                    padding: 8px 16px; border-radius: 4px; text-transform: uppercase;
                }}
                table {{ width: 100%; border-collapse: separate; border-spacing: 0 4px; font-size: 12px; }}
                th {{ font-family: 'JetBrains Mono'; color: var(--text-dim); text-transform: uppercase; font-size: 9px; padding: 10px; text-align: left; }}
                td {{ background: var(--plate-surface); padding: 12px 10px; border-top: 1px solid var(--plate-highlight); box-shadow: 2px 2px 5px var(--plate-shadow); }}
                td:first-child {{ border-radius: 4px 0 0 4px; }}
                td:last-child {{ border-radius: 0 4px 4px 0; }}
                td a {{ color: var(--accent-core); text-decoration: none; font-family: 'JetBrains Mono'; font-weight: 700; }}
            </style>
        </head>
        <body>
            <div class="tectonic-nav">
                <div class="repo-label">FIELD_DUMP // <span>REPOSITORY</span></div>
                <div>
                    <a href="/upload" class="back-btn" style="color:var(--accent-core); margin-right:5px;">+ UPLOAD</a>
                    <a href="/" class="back-btn">← DASH</a>
                </div>
            </div>
            <table>
                <thead>
                    <tr><th>File Name</th><th>Modified</th><th>Size</th><th>Action</th></tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            <script>
                async function purgeFile(name) {{
                    if(!confirm("Purge " + name + "?")) return;
                    await fetch('/api/terminal/run', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{ command: "rm /home/lockboxpi/dumps/" + name }})
                    }});
                    location.reload();
                }}
            </script>
        </body>
        </html>
        """
    except Exception as e:
        return f"Vault Error: {str(e)}"

# --- 5. SYSTEM STATS API ---
@app.route('/api/stats')
def get_stats_api():
    temp_val = "ERR"
    if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            celsius = int(f.read()) / 1000
            fahrenheit = (celsius * 9/5) + 32
            temp_val = str(round(fahrenheit, 1))
    
    ip = get_ip()
    mtk, usb_active = check_usb_devices()
    ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
    serial_status = "CONNECTED" if ports else "DISCONNECTED"
    
    adb = "NONE"
    if usb_active:
        try:
            adb_out = subprocess.check_output([ADB_BINARY, "devices"], timeout=2).decode().split('\n')
            adb = adb_out[1].split('\t')[0] if len(adb_out) > 1 and adb_out[1].strip() else "NONE"
        except: adb = "NONE"

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


@app.route('/tunnel/toggle', methods=['POST'])
def toggle_tunnel():
    current = get_tunnel_url()
    try:
        if current:
            subprocess.run(["sudo", "tailscale", "funnel", "off"])
            return jsonify(status="TUNNEL OFF")
        else:
            subprocess.run(["sudo", "tailscale", "funnel", "--bg", "8080"])
            return jsonify(status="TUNNEL ON")
    except Exception as e:
        return jsonify(status=f"ERROR: {str(e)}")

# --- 5.5 UDID ENROLLMENT RECEIVER ---
from flask import make_response

@app.route('/api/receive-udid', methods=['POST'])
def receive_udid():
    try:
        # 1. Capture the raw binary from the iPhone
        raw_payload = request.get_data()
        raw_path = os.path.join(DUMPS_DIR, "last_raw_enrollment.plist")
        with open(raw_path, "wb") as f:
            f.write(raw_payload)

        # 2. Run bash engine and capture its stdout directly
        #    (stdout = "udid=...&serial=...&model=...")
        result = subprocess.check_output(
            ["/bin/bash", BASH_ENGINE],
            stderr=subprocess.PIPE
        ).decode("utf-8").strip()

        # 3. Parse the key=value pairs the script echoes
        params = {}
        for pair in result.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                params[k.strip()] = v.strip()

        udid   = params.get("udid",   "UNKNOWN")
        serial = params.get("serial", "UNKNOWN")
        model  = params.get("model",  "UNKNOWN")

        # 4. Also write to file as fallback (bash already does this,
        #    but we write it here too so the redirect path is race-free)
        udid_path = os.path.join(DUMPS_DIR, "current_user_udid.txt")
        with open(udid_path, "w") as f:
            f.write(udid)

        # 5. Redirect — include HOST header so Safari follows to the right server.
        #    Use request.host so this works on any IP/port without hardcoding.
        host     = request.host                          # e.g. "192.168.1.42:5000"
        scheme   = request.scheme                        # "http" or "https"
        redirect_url = f"{scheme}://{host}/success-enroll"

        response = make_response("", 302)
        response.headers["Location"] = redirect_url
        # No-cache so Safari never serves a stale page
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return response

    except subprocess.CalledProcessError as e:
        logging.error(f"Bash engine failed: {e.stderr.decode()}")
        return "Enrollment script error", 500
    except Exception as e:
        logging.error(f"Enrollment Error: {e}")
        return "Internal Forensic Error", 500


@app.route('/success-enroll')
def success_enroll():
    udid_path = os.path.join(DUMPS_DIR, "current_user_udid.txt")

    if os.path.exists(udid_path):
        with open(udid_path, "r") as f:
            live_udid = f.read().strip()
    else:
        live_udid = "NO_ACTIVE_SESSION"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <!-- Tell Safari not to cache this page -->
    <meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <title>Hardware Vault</title>
    <style>
        :root {{
            --monolith-black: #0a0a0a;
            --anodized-grey: #1c1c1e;
            --machine-silver: #e2e2e2;
            --accent-blue: #007aff;
        }}
        body {{
            margin: 0; padding: 20px;
            background-color: #050505;
            display: flex; align-items: center; justify-content: center;
            min-height: 100vh;
            font-family: -apple-system, sans-serif;
        }}
        .monolith {{
            width: 100%; max-width: 400px;
            background: var(--anodized-grey);
            border-radius: 2px; padding: 30px;
            border: 1px solid rgba(255,255,255,0.05);
            box-shadow: 0 30px 60px rgba(0,0,0,0.8);
        }}
        .label {{
            font-size: 10px; font-weight: 800;
            color: rgba(255,255,255,0.3);
            text-transform: uppercase; letter-spacing: 2px;
        }}
        .value {{
            font-size: 18px; font-weight: 700;
            color: var(--machine-silver); margin-top: 5px;
        }}
        .id-well {{
            background: rgba(0,0,0,0.4); padding: 20px;
            border-radius: 4px;
            border-left: 3px solid var(--accent-blue);
            margin: 25px 0;
            box-shadow: inset 2px 2px 10px rgba(0,0,0,0.5);
        }}
        .udid-text {{
            font-family: 'SF Mono', 'JetBrains Mono', monospace;
            font-size: 12px; color: var(--accent-blue);
            word-break: break-all; line-height: 1.5;
            text-shadow: 0 0 10px rgba(0,122,255,0.3);
        }}
        .copy-btn {{
            width: 100%;
            background: linear-gradient(180deg, #3a3a3c 0%, #2c2c2e 100%);
            border: 1px solid rgba(255,255,255,0.1);
            color: var(--machine-silver);
            padding: 16px; font-weight: 700;
            text-transform: uppercase; cursor: pointer;
            border-radius: 4px; font-size: 12px; letter-spacing: 1px;
        }}
    </style>
</head>
<body>
    <div class="monolith">
        <div class="label">Hardware Vault</div>
        <div class="value">Identity Captured</div>

        <div class="id-well">
            <div class="udid-text" id="udid-val">{live_udid}</div>
        </div>

        <button class="copy-btn" onclick="copyId()">Copy Identifier</button>

        <p style="text-align:center; font-size:10px; color:rgba(255,255,255,0.2);
                  margin-top:25px; font-family:monospace;">
            SOURCE: DUMPS/CURRENT_USER_UDID.TXT<br>
            STATUS: SYNCED_TO_ALTSERVER
        </p>
    </div>
    <script>
        function copyId() {{
            const text = document.getElementById('udid-val').innerText;
            navigator.clipboard.writeText(text).then(() => {{
                const btn = document.querySelector('.copy-btn');
                btn.innerText = 'COPIED TO MEMORY';
                setTimeout(() => {{ btn.innerText = 'Copy Identifier'; }}, 2000);
            }}).catch(() => {{
                // Fallback for older Safari versions
                const el = document.getElementById('udid-val');
                const range = document.createRange();
                range.selectNode(el);
                window.getSelection().removeAllRanges();
                window.getSelection().addRange(range);
                document.execCommand('copy');
                const btn = document.querySelector('.copy-btn');
                btn.innerText = 'COPIED TO MEMORY';
                setTimeout(() => {{ btn.innerText = 'Copy Identifier'; }}, 2000);
            }});
        }}
    </script>
</body>
</html>"""

    response = make_response(html, 200)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


# --- 6. TERMINAL/COMMAND API ---
@app.route('/api/terminal/run', methods=['POST'])
def run_custom_command():
    cmd = request.json.get("command", "")
    if not cmd: return jsonify(status="error", output="Empty command")
    if cmd.startswith("mtk "): cmd = cmd.replace("mtk ", f"sudo {MTK_PYTHON} {MTK_SCRIPT} ", 1)
    elif cmd.startswith("knife "): cmd = cmd.replace("knife ", f"sudo {KNIFE_SCRIPT} ", 1)
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=60, cwd=DUMPS_DIR).decode('utf-8')
        return jsonify(status="success", output=output)
    except Exception as e: return jsonify(status="error", output=str(e))

# --- SYSTEM HELPERS ---
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

def get_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except: IP = '127.0.0.1'
    finally: s.close()
    return IP

def check_usb_devices():
    mtk = "DISCONNECTED"
    usb_active = False
    ignored_vids = ["1d6b", "0424", "2109", "1a40"]
    usb_path = "/sys/bus/usb/devices/"
    if not os.path.exists(usb_path): return mtk, usb_active
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
                except: continue
    except: pass
    return mtk, usb_active

def get_tunnel_url():
    try:
        result = subprocess.run(["tailscale", "funnel", "status"], capture_output=True, text=True, timeout=1)
        if "Funnel on" in result.stdout:
            return "https://lockboxtail.follow-deneb.ts.net"
    except: pass
    return None

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    subprocess.run(["pkill", "-9", "-f", "telegram_bot.py"])
    try:
        from telegram_bot import bot 
        
        def run_bot():
            while True:
                try:
                    bot.infinity_polling(skip_pending=True)
                except Exception as e:
                    logging.error(f"Bot polling error: {e}")
                    time.sleep(5)
                    
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        logging.info("--- TELEGRAM BOT ENGINE STARTED ---")
    except Exception as e:
        logging.error(f"FATAL: Bot failed to start: {e}")

    logging.info("--- FLASK HARDWARE BRIDGE STARTED ON PORT 5000 ---")
    app.run(host='0.0.0.0', port=5000, use_reloader=False)
