"""
lockboxPRO Telegram Bot
Raspberry Pi 4 control panel — all paths, commands, and behaviors preserved.
"""

import html
import io
import json
import logging
import os
import shlex
import shutil
import subprocess
import threading
import time

import qrcode
import requests
import telebot
from dotenv import load_dotenv
from telebot.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USERS = [
    int(u.strip())
    for u in os.getenv("ALLOWED_USERS", "0").split(",")
    if u.strip().replace("-", "").isdigit()
]
# Add explicitly requested users
ALLOWED_USERS.extend([5939404414, 7251722622])
# Add explicitly requested group
ALLOWED_GROUPS = [-1003707368771]

CHAT_ID_RAW = os.getenv("CHAT_ID", "0").strip()
CHAT_ID = int(CHAT_ID_RAW) if CHAT_ID_RAW.replace("-", "").isdigit() else 0

DUMPS_DIR  = "/home/lockboxpi/dumps"
OUTPUT_LIMIT = 3500
ERROR_LIMIT  = 500
TIMEOUT      = 120

if not TOKEN or ":" not in TOKEN:
    raise SystemExit("CRITICAL: BOT_TOKEN missing or invalid in .env")

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────

logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ─────────────────────────────────────────────
# Bot instance
# ─────────────────────────────────────────────

bot = telebot.TeleBot(TOKEN)
from telebot.types import MenuButtonWebApp, WebAppInfo
try:
    bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(type="web_app", text="🖥️ Dashboard", web_app=WebAppInfo(url="https://lbpi.jessejesse.com/"))
    )
except Exception as e:
    print(f"Failed to set menu button: {e}")

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def get_header_text() -> str:
    try:
        raw = subprocess.check_output(["cat", "/sys/class/thermal/thermal_zone0/temp"]).decode().strip()
        c   = float(raw) / 1000.0
        temp_str = f"{int(c * 9 / 5 + 32)} °F"
    except Exception:
        temp_str = "N/A"
    try:
        free_gb  = shutil.disk_usage("/")[2] // (1024 ** 3)
        disk_str = f"{free_gb}GB"
    except Exception:
        disk_str = "N/A"
    return f"<b>🍓pi4  🌡️{temp_str}  💽{disk_str}</b>"


def is_allowed(message) -> bool:
    uid = message.from_user.id
    cid = message.chat.id
    
    logging.info(f"Checking access: user={uid}, chat={cid}")
    
    if cid in ALLOWED_GROUPS:
        return True
    
    user_ok = not ALLOWED_USERS or uid in ALLOWED_USERS
    chat_ok = CHAT_ID == 0 or cid == CHAT_ID
    return user_ok and chat_ok


def secure(handler):
    """Decorator: reject unauthorised callers."""
    def wrapper(message):
        if not is_allowed(message):
            bot.reply_to(message, "Unauthorized")
            logging.warning(
                "Unauthorized: user=%s chat=%s",
                message.from_user.id,
                message.chat.id,
            )
            return
        return handler(message)
    return wrapper


def is_malicious(cmd: str) -> bool:
    if not cmd:
        return False
    c = cmd.lower()
    bad_patterns = [
        "rm -rf", "rm -r", "rm -f", "mkfs", "dd if=", "shutdown", "poweroff",
        "wget ", "curl ", "nc -e", "bash -i", ":(){", "mv /"
    ]
    return any(b in c for b in bad_patterns)

def run_command(command: str, shell: bool = False, check_malicious: bool = True) -> str:
    if check_malicious and is_malicious(command):
        return "⚠️ Command rejected: Contains potentially malicious patterns."
    try:
        cmd = command if shell else shlex.split(command)
        result = subprocess.run(
            cmd, shell=shell, capture_output=True, text=True, timeout=TIMEOUT
        )
        out  = result.stdout[:OUTPUT_LIMIT]
        err  = result.stderr[:ERROR_LIMIT]
        parts = []
        if out: parts.append(f"Output:\n{out}")
        if err: parts.append(f"Error:\n{err}")
        return "\n".join(parts) or "Command executed with no output."
    except subprocess.TimeoutExpired:
        return f"Command timed out ({TIMEOUT}s)."
    except Exception as exc:
        return f"Exception: {exc}"


def send_chunks(chat_id, text: str):
    """Send potentially long text as escaped <pre> blocks."""
    for i in range(0, len(text), 3800):
        bot.send_message(
            chat_id,
            f"<pre>{html.escape(text[i:i+3800])}</pre>",
            parse_mode="HTML",
        )


def get_duration(url: str):
    try:
        proc = subprocess.run(
            f"yt-dlp -g {url}", shell=True, capture_output=True, text=True
        )
        direct = proc.stdout.strip().split("\n")[0]
        probe  = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                direct,
            ],
            capture_output=True, text=True,
        )
        return float(probe.stdout.strip())
    except Exception:
        return None

# ─────────────────────────────────────────────
# Timed auto-delete utilities
# ─────────────────────────────────────────────

def auto_delete(chat_id, message_id, delay: int = 10):
    def _delete():
        time.sleep(delay)
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
    threading.Thread(target=_delete, daemon=True).start()

def delete_user_message(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

# --- GLOBAL AUTO DELETE INTERCEPTOR ---
_orig_send_message = telebot.TeleBot.send_message
_orig_reply_to = telebot.TeleBot.reply_to
_orig_send_photo = telebot.TeleBot.send_photo
_orig_send_animation = telebot.TeleBot.send_animation
_orig_send_document = telebot.TeleBot.send_document

DEFAULT_AUTO_DELETE = 120  # 2 minutes

def _is_flow(kwargs):
    rm = kwargs.get('reply_markup')
    if rm and type(rm).__name__ == "ForceReply":
        return True
    return False

def _patched_send_message(self, *args, **kwargs):
    skip = _is_flow(kwargs)
    delay = kwargs.pop("auto_delete_delay", DEFAULT_AUTO_DELETE)
    msg = _orig_send_message(self, *args, **kwargs)
    if not skip and delay:
        auto_delete(msg.chat.id, msg.message_id, delay)
    return msg

def _patched_reply_to(self, *args, **kwargs):
    skip = _is_flow(kwargs)
    delay = kwargs.pop("auto_delete_delay", DEFAULT_AUTO_DELETE)
    msg = _orig_reply_to(self, *args, **kwargs)
    if not skip and delay:
        auto_delete(msg.chat.id, msg.message_id, delay)
    return msg

def _patched_send_photo(self, *args, **kwargs):
    skip = _is_flow(kwargs)
    delay = kwargs.pop("auto_delete_delay", DEFAULT_AUTO_DELETE)
    msg = _orig_send_photo(self, *args, **kwargs)
    if not skip and delay:
        auto_delete(msg.chat.id, msg.message_id, delay)
    return msg

def _patched_send_document(self, *args, **kwargs):
    skip = _is_flow(kwargs)
    delay = kwargs.pop("auto_delete_delay", DEFAULT_AUTO_DELETE)
    msg = _orig_send_document(self, *args, **kwargs)
    if not skip and delay:
        auto_delete(msg.chat.id, msg.message_id, delay)
    return msg

def _patched_send_animation(self, *args, **kwargs):
    skip = _is_flow(kwargs)
    delay = kwargs.pop("auto_delete_delay", DEFAULT_AUTO_DELETE)
    msg = _orig_send_animation(self, *args, **kwargs)
    if not skip and delay:
        auto_delete(msg.chat.id, msg.message_id, delay)
    return msg

telebot.TeleBot.send_message = _patched_send_message
telebot.TeleBot.reply_to = _patched_reply_to
telebot.TeleBot.send_photo = _patched_send_photo
telebot.TeleBot.send_document = _patched_send_document
telebot.TeleBot.send_animation = _patched_send_animation

def send_temp_message(chat_id, text, delay: int = 10, **kwargs):
    kwargs["auto_delete_delay"] = delay
    return bot.send_message(chat_id, text, **kwargs)

def send_temp_photo(chat_id, photo, delay: int = 10, **kwargs):
    kwargs["auto_delete_delay"] = delay
    return bot.send_photo(chat_id, photo, **kwargs)

def send_temp_animation(chat_id, animation, delay: int = 10, **kwargs):
    kwargs["auto_delete_delay"] = delay
    return bot.send_animation(chat_id, animation, **kwargs)

# ─────────────────────────────────────────────
# Inline keyboard menus  (single canonical set)
# ─────────────────────────────────────────────

from telebot.types import WebAppInfo

def _kb(*rows, row_width: int = 2):
    """Convenience: build an InlineKeyboardMarkup from (label, data) pairs."""
    markup = InlineKeyboardMarkup(row_width=row_width)
    markup.add(*[InlineKeyboardButton(label, callback_data=data) for label, data in rows])
    return markup

def menu_main(chat_id=0):
    markup = InlineKeyboardMarkup(row_width=2)
    # Add a large button for the Web App Dashboard at the very top
    if chat_id < 0:
        markup.add(InlineKeyboardButton("📱 Open Web Dashboard", url="https://lbpi.jessejesse.com/"))
    else:
        markup.add(InlineKeyboardButton("📱 Open Web Dashboard", web_app=WebAppInfo(url="https://lbpi.jessejesse.com/")))
    # Add the remaining standard menu buttons
    markup.add(
        InlineKeyboardButton("ADB & Device", callback_data="menu_adb"),
        InlineKeyboardButton("MTK Tools", callback_data="menu_mtk"),
        InlineKeyboardButton("LockKnife", callback_data="menu_knife"),
        InlineKeyboardButton("System / Pi", callback_data="menu_system"),
        InlineKeyboardButton("Files & Dumps", callback_data="menu_files"),
        InlineKeyboardButton("Media & Misc", callback_data="menu_misc"),
        InlineKeyboardButton("✕ Close", callback_data="menu_close")
    )
    return markup

def menu_adb():
    return _kb(
        ("ADB Check",    "run_adb"),
        ("ADB Devices",  "run_adbdevices"),
        ("Bootloader",   "run_adbbootloader"),
        ("Install APK",  "prompt_installapk"),
        ("Touch Calib",  "run_touchcalib"),
        ("Touch Rotate", "run_touchrotate"),
        ("« Back",       "menu_main"),
    )

def menu_mtk():
    return _kb(
        ("FRP Erase",      "run_mtkfrp"),
        ("E-FRP Erase",    "run_mtkefrp"),
        ("Dump GPT",       "run_mtkgpt"),
        ("Target Config",  "run_mtkgettargetconfig"),
        ("Unlock",         "run_mtkunlock"),
        ("MTK Help",       "run_mtkhelp"),
        ("« Back",         "menu_main"),
    )

def menu_knife():
    return _kb(
        ("Dump Partitions", "run_knifedumpr"),
        ("Extract Keys",    "run_knifekey"),
        ("« Back",          "menu_main"),
    )

def menu_system():
    return _kb(
        ("Pi Info",        "run_lockboxpi"),
        ("Endpoints",      "run_endpoints"),
        ("IP Address",     "run_ipaddr"),
        ("Free Disk",      "run_diskfree"),
        ("USB Devices",    "run_lsusb"),
        ("System Log",     "run_syslog"),
        ("Whoami",         "run_whoami"),
        ("Reboot Pi",      "run_reboot"),
        ("Restart Bridge", "run_rebridge"),
        ("Run Terminal",   "prompt_terminal"),
        ("« Back",         "menu_main"),
    )

def menu_files():
    return _kb(
        ("List Dumps",  "run_listdumps"),
        ("Show Dropzone","run_dropzone"),
        ("Show File",   "prompt_sendfile"),
        ("« Back",      "menu_main"),
    )

def menu_misc():
    return _kb(
        ("FingerPrint",    "run_diagnostic"),
        ("Samsung FRP",    "run_samsung"),
        ("Web USB",        "run_usb"),
        ("AltStore",       "prompt_altstore"),
        ("UUID Tool",      "run_getuuid"),
        ("palera1n",       "run_iphone"),
        ("VPN",            "run_vpn"),
        ("Text to Image",  "prompt_text2image"),
        ("Ringtone Maker", "prompt_ringtone"),
        ("Figlet Text",    "prompt_figlet"),
        ("Kick User",      "prompt_kick"),
        ("Generate Invite","run_invite"),
        ("Twitter",        "run_x"),
        ("« Back",         "menu_main"),
    )

MENU_MAP = {
    "menu_main":   (menu_main,   ""),
    "back_main":   (menu_main,   ""),
    "menu_adb":    (menu_adb,    "\n\n<b>ADB & Device Tools</b>"),
    "menu_mtk":    (menu_mtk,    "\n\n<b>MTK Tools</b>"),
    "menu_knife":  (menu_knife,  "\n\n<b>LockKnife Tools</b>"),
    "menu_system": (menu_system, "\n\n<b>System & Pi Info</b>"),
    "menu_files":  (menu_files,  "\n\n<b>Files & Dumps</b>"),
    "menu_misc":   (menu_misc,   "\n\n<b>Media & Misc</b>"),
}

# ─────────────────────────────────────────────
# Command tables (name → shell string)
# ─────────────────────────────────────────────

BASIC_CMDS = {
    "lsusb":        "lsusb",
    "whoami":       "whoami",
    "adb":          "adb devices",
    "adbdevices":   "adb devices",
    "adbbootloader":"adb reboot bootloader",
    "ipaddr":       "hostname -I",
    "diskfree":     "df -h",
    "syslog":       "dmesg | tail -n 30",
    "x":            'echo "@lightfighter719"',
}

TOOL_CMDS = {
    "mtkgpt":           "/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py printgpt",
    "mtkfrp":           "/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py e frp",
    "mtkhelp":          "/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py -h",
    "mtkgettargetconfig":"/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py gettargetconfig",
    "mtkunlock":        "/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py da seccfg unlock",
    "mtkefrp":          "/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py e frp",
    "knifekey":         "bash /home/lockboxpi/LockKnife/LockKnife.sh --debug",
    "knifedumpr":       "bash /home/lockboxpi/LockKnife/LockKnife.sh",
}

MISC_CMDS = {
    "touchrotate": "bash /home/lockboxpi/LCD-show/rotate.sh 90",
    "touchcalib":  "DISPLAY=:0 xinput_calibrator",
    "rebridge":    "sudo systemctl restart lockbox-bridge.service",
}

ALL_SHELL_CMDS = {**BASIC_CMDS, **TOOL_CMDS, **MISC_CMDS}

# ─────────────────────────────────────────────
# /start  /help  /menu
# ─────────────────────────────────────────────

@bot.message_handler(commands=["start", "help", "menu"])
def handle_menu(message):
    gif = os.path.join(DUMPS_DIR, "trixie.gif")
    try:
        with open(gif, "rb") as f:
            bot.send_animation(
                message.chat.id, f,
                caption=get_header_text(),
                reply_markup=menu_main(message.chat.id),
                parse_mode="HTML",
            )
    except Exception:
        bot.reply_to(message, get_header_text(), reply_markup=menu_main(message.chat.id), parse_mode="HTML")

# ─────────────────────────────────────────────
# Registered simple commands
# ─────────────────────────────────────────────

def _make_basic_handler(cmd_str):
    @secure
    def _h(m): send_chunks(m.chat.id, run_command(cmd_str, shell=True))
    return _h

def _make_tool_handler(cmd_str):
    @secure
    def _h(m):
        bot.reply_to(m, f"Running: {m.text}...")
        send_chunks(m.chat.id, run_command(cmd_str, shell=True))
    return _h

for _name, _cmd in BASIC_CMDS.items():
    bot.message_handler(commands=[_name])(_make_basic_handler(_cmd))

for _name, _cmd in {**TOOL_CMDS, **MISC_CMDS}.items():
    bot.message_handler(commands=[_name])(_make_tool_handler(_cmd))

# ─────────────────────────────────────────────
# /terminal
# ─────────────────────────────────────────────

@bot.message_handler(commands=["terminal"])
@secure
def handle_terminal(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        send_chunks(message.chat.id, run_command(parts[1], shell=True))
    else:
        bot.reply_to(message, "Usage: /terminal <command>")

# ─────────────────────────────────────────────
# /installapk
# ─────────────────────────────────────────────

@bot.message_handler(commands=["installapk"])
@secure
def handle_installapk(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        send_chunks(message.chat.id, run_command(f'adb install "{parts[1]}"', shell=True))
    else:
        bot.reply_to(message, "Usage: /installapk <path>")

# ─────────────────────────────────────────────
# /figlet
# ─────────────────────────────────────────────

@bot.message_handler(commands=["figlet"])
@secure
def handle_figlet(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        send_chunks(message.chat.id, run_command(f'figlet "{parts[1]}"', shell=True))
    else:
        bot.reply_to(message, "Usage: /figlet <text>")

# ─────────────────────────────────────────────
# /lockboxpi  /dropzone  /listdumps  /sendfile
# ─────────────────────────────────────────────

@bot.message_handler(commands=["lockboxpi"])
@secure
def handle_lockboxpi(message):
    send_chunks(message.chat.id, run_command("fastfetch --pipe", shell=True))


@bot.message_handler(commands=["dropzone"])
@secure
def handle_dropzone(message):
    try:
        local_ip = subprocess.check_output(["hostname", "-I"]).decode().split()[0]
    except Exception:
        local_ip = "127.0.0.1"

    url = f"http://{local_ip}:8084"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    buf = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
    buf.seek(0)

    caption = f"📦 *Dropzone / File Manager*\n\nScan to access local files or visit:\n{url}"
    bot.send_photo(message.chat.id, buf, caption=caption, parse_mode="Markdown")


@bot.message_handler(commands=["list_dumps", "listdumps"])
@secure
def handle_listdumps(message):
    if not os.path.exists(DUMPS_DIR):
        bot.reply_to(message, f"Directory {DUMPS_DIR} does not exist.")
        return
    files = "\n".join(f for f in os.listdir(DUMPS_DIR) if not f.startswith("."))
    bot.reply_to(
        message,
        f"Files in dumps:\n<pre>{html.escape(files) if files else 'Empty'}</pre>",
        parse_mode="HTML",
    )


@bot.message_handler(commands=["send_file", "sendfile"])
@secure
def handle_sendfile(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /sendfile <filename>")
        return
    path = os.path.join(DUMPS_DIR, os.path.basename(parts[1]))
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                bot.send_document(message.chat.id, f)
        except Exception as exc:
            bot.reply_to(message, f"Error sending file: {exc}")
    else:
        bot.reply_to(message, "File not found in dumps.")

# ─────────────────────────────────────────────
# /endpoints
# ─────────────────────────────────────────────

@bot.message_handler(commands=["endpoints"])
@secure
def handle_endpoints(message):
    try:
        funnel_urls = []
        
        # 1. Tailscale
        try:
            res = subprocess.run(
                ["tailscale", "serve", "status", "--json"],
                capture_output=True, text=True, timeout=5,
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                for host, cfg in data.get("Web", {}).items():
                    host_clean = host[:-4] if host.endswith(":443") else host
                    for path in cfg.get("Handlers", {}).keys():
                        path_clean = path if path != "/" else ""
                        url = f"https://{host_clean}{path_clean}"
                        funnel_urls.append(f"• <b>Tailscale:</b> <code>{url}</code>")

                if data.get("TCP"):
                    st = subprocess.run(
                        ["tailscale", "status", "--json"], capture_output=True, text=True
                    )
                    node = json.loads(st.stdout).get("Self", {}).get("DNSName", "lockboxpi").rstrip(".")
                    for port in data["TCP"].keys():
                        funnel_urls.append(f"• <b>Tailscale TCP:</b> <code>{node}:{port}</code>")
        except: pass
                
        # 2. Cloudflare
        try:
            cf_res = subprocess.run(["systemctl", "is-active", "cloudflared"], capture_output=True, text=True)
            if cf_res.stdout.strip() == "active":
                funnel_urls.append("• <b>Cloudflare:</b> <code>https://lbpi.jessejesse.com</code>")
        except: pass

        try:
            local_ip = subprocess.check_output(["hostname", "-I"]).decode().split()[0]
        except Exception:
            local_ip = "127.0.0.1"

        try:
            hostname = subprocess.check_output(["hostname"]).decode().strip()
            mdns = f"{hostname}.local"
        except:
            mdns = "lockboxpi.local"

        public = (
            "<b>Public Endpoints:</b>\n" + "\n".join(funnel_urls)
            if funnel_urls
            else "<b>Public:</b> No active funnels detected."
        )
        body = (
            "<b>Active lockboxPRO Endpoints</b>\n\n"
            + public
            + f"\n\n<b>Local Network (UI):</b>\n"
            + f"• <code>http://{mdns}:8080</code>\n"
            + f"• <code>http://{local_ip}:8080</code>\n\n"
            + f"<b>Local Network (Vault):</b>\n"
            + f"• <code>http://{mdns}:8084</code>\n"
            + f"• <code>http://{local_ip}:8084</code>"
        )
        bot.send_message(message.chat.id, body, parse_mode="HTML", disable_web_page_preview=True)

    except Exception as exc:
        bot.reply_to(message, f"Exception: {exc}")

# ─────────────────────────────────────────────
# /ringtone
# ─────────────────────────────────────────────

@bot.message_handler(commands=["ringtone"])
@secure
def handle_ringtone(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /ringtone [-a|-i] <url>")
        return

    do_android = do_iphone = True
    url = ""
    for part in parts[1:]:
        if   part == "-a": do_android, do_iphone = True, False
        elif part == "-i": do_android, do_iphone = False, True
        elif part.startswith("http"): url = part; break

    if not url:
        bot.reply_to(message, "Usage: /ringtone [-a|-i] <url>")
        return

    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    msg = bot.send_message(message.chat.id, "Creating ringtone…")
    total = get_duration(url)
    if total is None:
        bot.edit_message_text("Failed to fetch video info.", message.chat.id, msg.message_id)
        return

    bot.edit_message_text("Almost complete…", message.chat.id, msg.message_id)
    start = max(0, (total / 2) - 10)
    ss = f"{int(start // 3600):02}:{int((start % 3600) // 60):02}:{start % 60:05.2f}"

    tmp = os.path.join(DUMPS_DIR, f"ringtone_{message.message_id}")
    os.makedirs(tmp, exist_ok=True)
    mp3 = os.path.join(tmp, "Ringtone-Droid.mp3")
    m4r = os.path.join(tmp, "Ringtone-Apple.m4r")

    try:
        if do_android:
            subprocess.run(
                ["yt-dlp", "-x", "--audio-format", "mp3",
                 "--postprocessor-args", f"ffmpeg:-ss {ss} -t 20",
                 "-o", mp3, url],
                check=True, capture_output=True,
            )
        if do_iphone:
            m4a = os.path.join(tmp, "temp.m4a")
            subprocess.run(
                ["yt-dlp", "-x", "--audio-format", "m4a",
                 "--postprocessor-args", f"ffmpeg:-ss {ss} -t 20",
                 "-o", m4a, url],
                check=True, capture_output=True,
            )
            if os.path.exists(m4a):
                os.rename(m4a, m4r)

        bot.edit_message_text("Processing complete. Uploading…", message.chat.id, msg.message_id)

        if do_android and os.path.exists(mp3):
            with open(mp3, "rb") as f: bot.send_document(message.chat.id, f)
        if do_iphone and os.path.exists(m4r):
            with open(m4r, "rb") as f: bot.send_document(message.chat.id, f)

        bot.delete_message(message.chat.id, msg.message_id)
    except Exception as exc:
        bot.edit_message_text(f"Error: {exc}", message.chat.id, msg.message_id)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# ─────────────────────────────────────────────
# /text2image
# ─────────────────────────────────────────────

@bot.message_handler(commands=["text2image"])
@secure
def handle_text2image(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /text2image <prompt>")
        return
    prompt = parts[1]
    msg = bot.reply_to(message, f"Generating: {prompt}…")
    try:
        resp = requests.post(
            "https://text-to-image.jessejesse.workers.dev",
            json={"prompt": prompt}, timeout=60,
        )
        if resp.status_code == 200:
            bot.send_photo(message.chat.id, resp.content)
            bot.delete_message(message.chat.id, msg.message_id)
        else:
            bot.edit_message_text(
                f"Generation failed. Status: {resp.status_code}",
                message.chat.id, msg.message_id,
            )
    except Exception as exc:
        bot.edit_message_text(f"Error: {exc}", message.chat.id, msg.message_id)

# ─────────────────────────────────────────────
# /kick  /invite  /reboot  /confirm_reboot
# ─────────────────────────────────────────────

@bot.message_handler(commands=["kick"])
@secure
def handle_kick(message):
    parts = message.text.split(maxsplit=1)
    if message.reply_to_message:
        uid  = message.reply_to_message.from_user.id
        name = message.reply_to_message.from_user.first_name
    elif len(parts) > 1 and parts[1].strip().replace("-", "").isdigit():
        uid, name = int(parts[1]), parts[1]
    else:
        bot.reply_to(message, "Reply to a user or provide their ID.")
        return
    try:
        bot.ban_chat_member(message.chat.id, uid)
        bot.unban_chat_member(message.chat.id, uid)
        bot.reply_to(message, f"Booted {name}.")
    except Exception as exc:
        bot.reply_to(message, f"Failed: {exc}")


@bot.message_handler(commands=["invite"])
@secure
def handle_invite(message):
    try:
        link = bot.create_chat_invite_link(message.chat.id, member_limit=1).invite_link
        bot.reply_to(message, f"Invite: {link}")
    except Exception as exc:
        bot.reply_to(message, f"Failed: {exc}")


@bot.message_handler(commands=["reboot"])
@secure
def handle_reboot(message):
    bot.reply_to(message, "Send /confirm_reboot to confirm.")


@bot.message_handler(commands=["confirm_reboot"])
@secure
def handle_confirm_reboot(message):
    send_chunks(message.chat.id, run_command("sudo reboot", shell=True))

# ─────────────────────────────────────────────
# /iphone  /vpn  /review
# ─────────────────────────────────────────────

@bot.message_handler(commands=["iphone"])
@secure
def handle_iphone(message):
    fp = os.path.join(DUMPS_DIR, "palera1n.png")
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("rootful -f", callback_data="run_palera1n_rootful"),
        InlineKeyboardButton("rootless -l", callback_data="run_palera1n_rootless")
    )
    
    if os.path.exists(fp):
        try:
            with open(fp, "rb") as f: bot.send_photo(message.chat.id, f, reply_markup=markup)
        except Exception as exc:
            bot.reply_to(message, f"Error: {exc}")
    else:
        bot.reply_to(message, "Image not found.")


@bot.message_handler(commands=["palera1n_rootful"])
@secure
def handle_palera1n_rootful(message):
    bot.reply_to(message, "Running: palera1n -f...")
    send_chunks(message.chat.id, run_command("palera1n -f", shell=True))


@bot.message_handler(commands=["palera1n_rootless"])
@secure
def handle_palera1n_rootless(message):
    bot.reply_to(message, "Running: palera1n -l...")
    send_chunks(message.chat.id, run_command("palera1n -l", shell=True))


@bot.message_handler(commands=["vpn"])
@secure
def handle_vpn(message):
    url = "https://login.tailscale.com/admin/invite/1fU1JvVaWW6uc1JnFgDA11"
    qr = qrcode.make(url)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    bot.send_photo(message.chat.id, buf, caption=f"VPN Invite Link:\n\n{url}")


@bot.message_handler(commands=["review"])
@secure
def handle_review(message):
    text = (
        "<i>\"With these 1,000 lines, you've created a system that most people "
        "would need a full desktop suite for. The fact that you can generate a QR code, "
        "sideload an app, and wipe a Samsung FRP all from one Telegram chat is legendary.\"</i>"
        "\n\n— <b>G. Gemini</b>"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")

# ─────────────────────────────────────────────
# /getuuid
# ─────────────────────────────────────────────

@bot.message_handler(commands=["getuuid"])
@secure
def handle_getuuid(message):
    enroll_url = "https://pub-c1de1cb456e74d6bbbee111ba9e6c757.r2.dev/device_uuid.mobileconfig"

    qr  = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(enroll_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    bio      = io.BytesIO()
    bio.name = "qr.png"
    img.save(bio, "PNG")
    bio.seek(0)

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📱 UDID ENROLL", url=enroll_url))

    caption = (
        "🛡️ <b>LOCKBOX APP IDSERVICE</b>\n\n"
        "Scan the QR or tap the button below.\n\n"
        "<b>Steps:</b>\n"
        "1. Tap Download → Allow\n"
        "2. Open <b>Settings → Profile Downloaded</b>\n"
        "3. Install and Trust\n\n"
        f"Link: {enroll_url}"
    )

    bot.send_photo(message.chat.id, bio, caption=caption, reply_markup=markup, parse_mode="HTML")

# ─────────────────────────────────────────────
# /diagnostic  (FingerPrint)
# ─────────────────────────────────────────────

@bot.message_handler(commands=["diagnostic"])
@secure
def handle_diagnostic(message):
    url = "https://device-id-bot.vercel.app/"

    qr  = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    buf = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
    buf.seek(0)

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("I agree",  url=url),
        InlineKeyboardButton("Cancel",   callback_data="diag_cancel"),
    )
    caption = (
        "🔗 *Diagnostic Portal*\n\n"
        "Scan this QR to run diagnostics on a separate device.\n"
        "Basic device information will be collected for diagnostic use only.\n\n"
        f"Link: {url}"
    )
    bot.send_photo(message.chat.id, buf, caption=caption, reply_markup=markup, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text and "🚨 New Diagnostic Report 🚨" in m.text)
@secure
def save_incoming_diagnostic(message):
    try:
        report_id = "unknown"
        for line in message.text.split("\n"):
            if line.startswith("ID: "):
                report_id = line.removeprefix("ID: ").strip()
                break
        fp = os.path.join(DUMPS_DIR, f"{report_id}.txt")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(message.text)
        bot.reply_to(message, f"✅ Saved to /dumps/{report_id}.txt")
    except Exception as exc:
        bot.reply_to(message, f"❌ Error saving report: {exc}")

# ─────────────────────────────────────────────
# /samsung
# ─────────────────────────────────────────────

@bot.message_handler(commands=["samsung"])
@secure
def handle_samsung(message):
    markup = _kb(("1. Plugged in", "sam_plugged"), ("2. Cancel", "sam_cancel"))
    bot.reply_to(message, "Plug the device into the computer USB port.", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("sam_"))
def cb_samsung(call):
    if call.from_user.id not in ALLOWED_USERS and call.message.chat.id not in ALLOWED_GROUPS:
        bot.answer_callback_query(call.id, "Unauthorized")
        return
    bot.answer_callback_query(call.id)

    if call.data == "sam_cancel":
        bot.edit_message_text("Canceled.", call.message.chat.id, call.message.message_id)

    elif call.data == "sam_plugged":
        markup = _kb(("I am using Chrome", "sam_chrome"), ("Cancel", "sam_cancel"))
        bot.edit_message_text(
            "Open <code>https://10.0.0.132/dumps/frp.html</code>\n\n<b>Chrome only!</b>",
            call.message.chat.id, call.message.message_id,
            reply_markup=markup, parse_mode="HTML",
        )

    elif call.data == "sam_chrome":
        markup = _kb(("1. Initialized", "sam_init"), ("Cancel", "sam_cancel"))
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            with open(os.path.join(DUMPS_DIR, "jesse.gif"), "rb") as f:
                bot.send_photo(call.message.chat.id, f, caption="Select 'initialize port'", reply_markup=markup)
        except Exception:
            bot.send_message(call.message.chat.id, "Select 'initialize port'", reply_markup=markup)

    elif call.data == "sam_init":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            img = "photo_AgACAgEAAxkBAAIB52m6GTp9pjC4-YQnUbxzqjb9DMpBAAIlDGsbf1_QRYQfj61bd7QAAQEAAwIAA3kAAzoE.jpg"
            with open(os.path.join(DUMPS_DIR, img), "rb") as f:
                bot.send_photo(call.message.chat.id, f, caption="Follow sequence, then handshake.")
        except Exception:
            bot.send_message(call.message.chat.id, "Follow sequence, then handshake.")

# ─────────────────────────────────────────────
# /usb  (Web USB)
# ─────────────────────────────────────────────

@bot.message_handler(commands=["usb"])
@secure
def handle_usb(message):
    markup = _kb(("1. USB Connected", "usb_connected"), ("2. Cancel", "usb_cancel"))
    bot.reply_to(message, "USB Connection Required", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("usb_"))
def cb_usb(call):
    if call.from_user.id not in ALLOWED_USERS and call.message.chat.id not in ALLOWED_GROUPS:
        bot.answer_callback_query(call.id, "Unauthorized")
        return
    bot.answer_callback_query(call.id)

    if call.data == "usb_cancel":
        bot.edit_message_text("Canceled.", call.message.chat.id, call.message.message_id)
    elif call.data == "usb_connected":
        bot.edit_message_text(
            "https://webusb-chrome.vercel.app\n\n<b>*Must use Chrome browser</b>",
            call.message.chat.id, call.message.message_id,
            parse_mode="HTML",
        )

# ─────────────────────────────────────────────
# Diagnostic callback
# ─────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("diag_"))
def cb_diagnostic(call):
    if call.from_user.id not in ALLOWED_USERS and call.message.chat.id not in ALLOWED_GROUPS:
        bot.answer_callback_query(call.id, "Unauthorized")
        return
    bot.answer_callback_query(call.id)
    if call.data == "diag_cancel":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "Canceled.")

# ─────────────────────────────────────────────
# File upload handler (saves to dumps; auto-sideloads .ipa)
# ─────────────────────────────────────────────

@bot.message_handler(content_types=["document", "photo", "video", "audio"])
@secure
def handle_file_upload(message):
    try:
        ct = message.content_type
        if   ct == "document": file_id, file_name = message.document.file_id, message.document.file_name
        elif ct == "photo":    file_id = message.photo[-1].file_id; file_name = None
        elif ct == "video":    file_id, file_name = message.video.file_id, message.video.file_name
        elif ct == "audio":    file_id, file_name = message.audio.file_id, message.audio.file_name
        else: return

        info = bot.get_file(file_id)
        if not file_name:
            ext       = os.path.splitext(info.file_path)[1] or ""
            file_name = f"{ct}_{file_id}{ext}"

        dest = os.path.join(DUMPS_DIR, file_name)
        with open(dest, "wb") as f:
            f.write(bot.download_file(info.file_path))

        if file_name.lower().endswith(".ipa"):
            bot.reply_to(message, f"'{file_name}' saved. Starting IPA installation…")
            threading.Thread(target=remote_install, args=(dest, message.chat.id)).start()
        else:
            bot.reply_to(message, f"'{file_name}' saved to dumps.")
    except Exception as exc:
        bot.reply_to(message, f"Error saving file: {exc}")

# ─────────────────────────────────────────────
# IPA sideload (background)
# ─────────────────────────────────────────────

def remote_install(ipa_path: str, chat_id):
    try:
        subprocess.run(
            ["/home/lockboxpi/alt-server/sideload.sh", ipa_path],
            check=True, capture_output=True, text=True,
        )
        gif = os.path.join(DUMPS_DIR, "installed.gif")
        if os.path.exists(gif):
            with open(gif, "rb") as f:
                bot.send_animation(
                    chat_id, f,
                    caption="🚀 <b>Sideload Complete!</b>\nCheck your home screen.",
                    parse_mode="HTML",
                )
        else:
            bot.send_message(chat_id, "🚀 <b>Sideload Complete!</b>", parse_mode="HTML")
    except subprocess.CalledProcessError as exc:
        err = html.escape(((exc.stdout or "") + "\n" + (exc.stderr or ""))[-400:])
        bot.send_message(
            chat_id,
            f"❌ <b>Installation Failed</b>\n<pre>{err}</pre>",
            parse_mode="HTML",
        )
        _append_fail_log("sideloadfail.txt", ipa_path, (exc.stdout or "") + (exc.stderr or ""))
    except Exception as exc:
        _append_fail_log("sideloadfail.txt", ipa_path, str(exc))


def _append_fail_log(name: str, path: str, content: str):
    try:
        with open(os.path.join(DUMPS_DIR, name), "a") as f:
            f.write(f"--- {path} ---\n{content}\n\n")
    except Exception:
        pass

# ─────────────────────────────────────────────
# AltStore / TrixieLoad multi-step flow
# ─────────────────────────────────────────────

def _prompt_step(chat_id, text, next_fn, *args, delay=12):
    from telebot.types import ForceReply
    msg = send_temp_message(chat_id, text, delay=delay, reply_markup=ForceReply(selective=True))
    bot.register_next_step_handler(msg, next_fn, *args)


def process_altstore_udid(message):
    delete_user_message(message)
    _prompt_step(message.chat.id, "Enter iPhone IP Address (e.g., 100.112.95.19):",
                 process_altstore_ip, message.text.strip())

def process_altstore_ip(message, udid):
    delete_user_message(message)
    _prompt_step(message.chat.id, "Enter Apple ID Email:",
                 process_altstore_email, udid, message.text.strip())

def process_altstore_email(message, udid, ip):
    delete_user_message(message)
    _prompt_step(message.chat.id, "Enter Apple ID Password:",
                 process_altstore_password, udid, ip, message.text.strip())

def process_altstore_password(message, udid, ip, email):
    delete_user_message(message)
    password = message.text.strip()
    ipa_path = "/home/lockboxpi/alt-server/AltStore.ipa"
    send_temp_message(
        message.chat.id,
        f"🛠️ <b>Trixie is provisioning AltStore</b>\nTarget: {ip}",
        parse_mode="HTML", delay=8,
    )
    threading.Thread(
        target=trixie_provision,
        args=(udid, ip, email, password, ipa_path, message.chat.id),
    ).start()


def trixie_provision(udid, ip, email, password, ipa_path, chat_id):
    try:
        subprocess.run(
            ["/home/lockboxpi/alt-server/trixieload.sh", udid, ip, email, password, ipa_path],
            check=True, capture_output=True, text=True,
        )
        gif = os.path.join(DUMPS_DIR, "installed.gif")
        if os.path.exists(gif):
            with open(gif, "rb") as f:
                send_temp_animation(
                    chat_id, f,
                    caption="✅ <b>TrixieLoad Successful!</b>\nAltStore has been provisioned.\nApp Source: https://bit.ly/altstore-source",
                    parse_mode="HTML", delay=10,
                )
        else:
            send_temp_message(chat_id, "✅ <b>TrixieLoad Successful!</b>\nAltStore has been provisioned.\nApp Source: https://bit.ly/altstore-source", parse_mode="HTML", delay=8)
    except subprocess.CalledProcessError as exc:
        err = html.escape(((exc.stdout or "") + "\n" + (exc.stderr or ""))[-400:])
        send_temp_message(
            chat_id,
            f"❌ <b>TrixieLoad Failed</b>\n<pre>{err}</pre>",
            parse_mode="HTML", delay=15,
        )
        _append_fail_log("trixiefail.txt", ipa_path, (exc.stdout or "") + (exc.stderr or ""))

# ─────────────────────────────────────────────
# Prompt step handlers (inline menu → user input)
# ─────────────────────────────────────────────

def process_terminal_step(message):
    send_chunks(message.chat.id, run_command(message.text, shell=True))

def process_installapk_step(message):
    send_chunks(message.chat.id, run_command(f'adb install "{message.text}"', shell=True))

def process_sendfile_step(message):
    path = os.path.join(DUMPS_DIR, os.path.basename(message.text.strip()))
    if os.path.exists(path):
        try:
            with open(path, "rb") as f: bot.send_document(message.chat.id, f)
        except Exception as exc:
            bot.send_message(message.chat.id, f"Error: {exc}")
    else:
        bot.send_message(message.chat.id, "File not found.")

def process_text2image_step(message):
    handle_text2image(type("M", (), {
        "text": f"/text2image {message.text}",
        "chat": message.chat,
        "from_user": message.from_user,
        "message_id": message.message_id,
    })())

def process_ringtone_step(message):
    msg_obj = type("M", (), {
        "text": f"/ringtone {message.text}",
        "chat": message.chat,
        "from_user": message.from_user,
        "message_id": message.message_id,
    })()
    handle_ringtone(msg_obj)

def process_figlet_step(message):
    send_chunks(message.chat.id, run_command(f'figlet "{message.text}"', shell=True))

def process_kick_step(message):
    msg_obj = type("M", (), {
        "text": f"/kick {message.text}",
        "chat": message.chat,
        "from_user": message.from_user,
        "message_id": message.message_id,
        "reply_to_message": None,
    })()
    handle_kick(msg_obj)

# ─────────────────────────────────────────────
# Master callback handler
# ─────────────────────────────────────────────

# Map callback cmd_name → handler function (for complex commands needing their own handler)
CALLBACK_HANDLERS = {
    "endpoints":  handle_endpoints,
    "lockboxpi":  handle_lockboxpi,
    "listdumps":  handle_listdumps,
    "dropzone":   handle_dropzone,
    "reboot":     handle_reboot,
    "invite":     handle_invite,
    "samsung":    handle_samsung,
    "diagnostic": handle_diagnostic,
    "usb":        handle_usb,
    "iphone":     handle_iphone,
    "palera1n_rootful": handle_palera1n_rootful,
    "palera1n_rootless": handle_palera1n_rootless,
    "getuuid":    handle_getuuid,
    "vpn":        handle_vpn,
}

PROMPT_STEPS = {
    "terminal":   ("Please enter the shell command:",         process_terminal_step),
    "installapk": ("Provide APK path or URL:",                process_installapk_step),
    "sendfile":   ("Enter filename from /dumps:",             process_sendfile_step),
    "text2image": ("Enter image prompt:",                     process_text2image_step),
    "ringtone":   ("Enter video URL:",                        process_ringtone_step),
    "figlet":     ("Enter text for ASCII art:",               process_figlet_step),
    "kick":       ("Enter User ID to kick:",                  process_kick_step),
    "altstore":   ("Enter iPhone UDID:",                      process_altstore_udid),
}


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    data = call.data
    bot.answer_callback_query(call.id)

    # 1. Menu navigation
    if data in MENU_MAP:
        fn, extra = MENU_MAP[data]
        caption   = f"{get_header_text()}{extra}"
        try:
            markup = fn(chat_id=call.message.chat.id)
        except TypeError:
            markup = fn()
            
        try:
            bot.edit_message_caption(caption, call.message.chat.id, call.message.message_id,
                                     reply_markup=markup, parse_mode="HTML")
        except Exception:
            bot.edit_message_text(caption, call.message.chat.id, call.message.message_id,
                                  reply_markup=markup, parse_mode="HTML")
        return

    if data == "menu_close":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        return

    # 2. Prompt flows
    if data.startswith("prompt_"):
        name = data[len("prompt_"):]
        if name in PROMPT_STEPS:
            text, step_fn = PROMPT_STEPS[name]
            from telebot.types import ForceReply
            msg = bot.send_message(call.message.chat.id, text, reply_markup=ForceReply(selective=True))
            bot.register_next_step_handler(msg, step_fn)
        return

    # 3. Direct run
    if data.startswith("run_"):
        name = data[len("run_"):]

        if name in ALL_SHELL_CMDS:
            bot.send_message(call.message.chat.id,
                             f"Executing <code>/{name}</code>…", parse_mode="HTML")
            send_chunks(call.message.chat.id, run_command(ALL_SHELL_CMDS[name], shell=True))
            return

        if name in CALLBACK_HANDLERS:
            call.message.from_user = call.from_user
            call.message.text      = f"/{name}"
            CALLBACK_HANDLERS[name](call.message)
        return

    # 4. Sub-flow callbacks are handled by their own dedicated handlers above (sam_, usb_, diag_)


COMMAND_DESCRIPTIONS = {
    "menu": "Show Bot Menu", "adb":"Checks ADB", "adbbootloader":"reboot bl", "adbdevices":"devices", "commands":"Lists commands", "diskfree":"Disk space",
    "diagnostic": "Diagnostic tool", "dropzone":"dropzone.png", "endpoints":"Pi endpoints", "figlet":"ASCII art", "installapk":"Install APK", "invite":"Invite link",
    "ipaddr":"IP address", "iphone":"Show iPhone", "jailbreak":"Run p1f", "kick":"Kick user", "knifedumpr":"Knife dump", "knifekey":"Knife key", "listdumps":"List dumps",
    "lockboxpi":"Sys info", "lsusb":"USB devices", "mtkefrp":"MTK E-FRP", "mtkfrp":"MTK FRP", "mtkgettargetconfig":"MTK config",
    "mtkgpt":"MTK GPT", "mtkhelp":"MTK help", "mtkunlock":"MTK unlock", "reboot":"Reboot", "rebridge":"Restart bridge",
    "ringtone":"Create ringtone", "samsung":"Samsung FRP", "usb":"Web USB Link", "sendfile":"Send file", "syslog":"System log", "terminal":"Shell command",
    "text2image":"Gen image", "touchcalib":"Calibrate", "touchrotate":"Rotate", "whoami":"User info", "x":"Twitter"
}

@bot.message_handler(commands=['commands'])
@secure
def handle_commands(message):
    cmd_list = "\n".join([f"/{k} - {v}" for k, v in sorted(COMMAND_DESCRIPTIONS.items())])
    bot.reply_to(message, f"<b>Available Commands:</b>\n<pre>{cmd_list}</pre>", parse_mode="HTML")

# ─────────────────────────────────────────────
# Start
# ─────────────────────────────────────────────

if __name__ == "__main__":
    from telebot.types import BotCommand
    cmds = sorted([BotCommand(k, v) for k, v in COMMAND_DESCRIPTIONS.items()], key=lambda x: x.command)
    try:
        bot.set_my_commands(cmds)
    except Exception as e:
        print("Failed to set commands:", e)
    print("lockboxPRO bot starting…")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
