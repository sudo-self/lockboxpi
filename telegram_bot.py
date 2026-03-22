import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
import subprocess
import os
import json
import requests
import shlex
import logging
import shutil
import qrcode
import io

# --- Configuration ---
TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ALLOWED_USERS_RAW = os.getenv('ALLOWED_USERS', '0')
ALLOWED_USERS = [int(u.strip()) for u in ALLOWED_USERS_RAW.split(',') if u.strip().replace('-', '').isdigit()]
CHAT_ID_RAW = os.getenv('CHAT_ID', '0')
CHAT_ID = int(CHAT_ID_RAW.strip()) if CHAT_ID_RAW.strip().replace('-', '').isdigit() else 0
DUMPS_DIR = '/var/www/dumps'
OUTPUT_LIMIT = 3500
ERROR_LIMIT = 500
TIMEOUT = 120
def get_header_text():
    try:
        temp_c = float(subprocess.check_output(['cat', '/sys/class/thermal/thermal_zone0/temp']).decode('utf-8').strip()) / 1000.0
        temp_f = (temp_c * 9/5) + 32
        temp_str = f"{int(temp_f)} °F"
    except Exception:
        temp_str = "N/A"
    try:
        free_bytes = shutil.disk_usage("/")[2]
        free_space = f"{int(free_bytes / (1024**3))}GB"
    except Exception:
        free_space = "N/A"
    return f"<b>🍓RPi4  🌡️{temp_str}  💾 {free_space}</b>"


bot = telebot.TeleBot(TOKEN)

# --- Logging ---
logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# --- Helpers ---
def is_allowed(message):
    user_ok = (len(ALLOWED_USERS) == 0) or (message.from_user.id in ALLOWED_USERS)
    chat_ok = (CHAT_ID == 0) or (message.chat.id == CHAT_ID)
    return user_ok and chat_ok

def run_command(command, shell=False):
    try:
        if not shell:
            cmd_list = shlex.split(command)
        else:
            cmd_list = command
        result = subprocess.run(cmd_list, shell=shell, capture_output=True, text=True, timeout=TIMEOUT)
        output = result.stdout[:OUTPUT_LIMIT]
        error = result.stderr[:ERROR_LIMIT]
        response = ''
        if output:
            response += f"Output:\n{output}\n"
        if error:
            response += f"Error:\n{error}\n"
        return response if response else "Command executed successfully with no output."
    except subprocess.TimeoutExpired:
        return f"Command timed out ({TIMEOUT}s limit)."
    except Exception as e:
        return f"Exception occurred: {str(e)}"

def secure(handler):
    def wrapper(message):
        if not is_allowed(message):
            bot.reply_to(message, "Unauthorized")
            logging.warning(f"Unauthorized access attempt by {message.from_user.id} in chat {message.chat.id}")
            return
        return handler(message)
    return wrapper

def send_chunks(chat_id, text):
    import html
    # Reduce chunk size to account for HTML escaping expansion
    for i in range(0, len(text), 3800):
        bot.send_message(chat_id, f"<pre>{html.escape(text[i:i+3800])}</pre>", parse_mode="HTML")

def get_duration(url):
    try:
        proc = subprocess.run(f"yt-dlp -g {url}", shell=True, capture_output=True, text=True)
        direct_url = proc.stdout.strip().split('\n')[0]
        probe = subprocess.run([
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', direct_url
        ], capture_output=True, text=True)
        return float(probe.stdout.strip())
    except:
        return None

# --- UI Menus ---
def get_main_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("ADB & Device", callback_data="menu_adb"),
        InlineKeyboardButton("MTK Tools", callback_data="menu_mtk"),
        InlineKeyboardButton("LockKnife", callback_data="menu_knife"),
        InlineKeyboardButton("System / Pi", callback_data="menu_system"),
        InlineKeyboardButton("Files & Dumps", callback_data="menu_files"),
        InlineKeyboardButton("Media & Misc", callback_data="menu_misc"),
        InlineKeyboardButton("Dismiss Menu", callback_data="menu_close")
    )
    return markup

def get_adb_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("ADB Check", callback_data="run_adb"),
        InlineKeyboardButton("ADB Devices", callback_data="run_adbdevices"),
        InlineKeyboardButton("Bootloader", callback_data="run_adbbootloader"),
        InlineKeyboardButton("Install APK", callback_data="prompt_installapk"),
        InlineKeyboardButton("Touch Calib", callback_data="run_touchcalib"),
        InlineKeyboardButton("Touch Rotate", callback_data="run_touchrotate"),
        InlineKeyboardButton("« Back", callback_data="menu_main")
    )
    return markup

def get_mtk_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("FRP Erase", callback_data="run_mtkfrp"),
        InlineKeyboardButton("E-FRP Erase", callback_data="run_mtkefrp"),
        InlineKeyboardButton("Dump GPT", callback_data="run_mtkgpt"),
        InlineKeyboardButton("Target Config", callback_data="run_mtkgettargetconfig"),
        InlineKeyboardButton("Unlock", callback_data="run_mtkunlock"),
        InlineKeyboardButton("MTK Help", callback_data="run_mtkhelp"),
        InlineKeyboardButton("« Back", callback_data="menu_main")
    )
    return markup

def get_knife_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Dump Partitions", callback_data="run_knifedumpr"),
        InlineKeyboardButton("Extract Keys", callback_data="run_knifekey"),
        InlineKeyboardButton("« Back", callback_data="menu_main")
    )
    return markup

def get_system_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Pi Info", callback_data="run_lockboxpi"),
        InlineKeyboardButton("Endpoints", callback_data="run_endpoints"),
        InlineKeyboardButton("IP Address", callback_data="run_ipaddr"),
        InlineKeyboardButton("Free Disk", callback_data="run_diskfree"),
        InlineKeyboardButton("USB Devices", callback_data="run_lsusb"),
        InlineKeyboardButton("System Log", callback_data="run_syslog"),
        InlineKeyboardButton("Whoami", callback_data="run_whoami"),
        InlineKeyboardButton("Reboot Pi", callback_data="run_reboot"),
        InlineKeyboardButton("Restart Bridge", callback_data="run_rebridge"),
        InlineKeyboardButton("Run Terminal", callback_data="prompt_terminal"),
        InlineKeyboardButton("« Back", callback_data="menu_main")
    )
    return markup

def get_files_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("List Dumps", callback_data="run_listdumps"),
        InlineKeyboardButton("Show Dropzone", callback_data="run_dropzone"),
        InlineKeyboardButton("Send File", callback_data="prompt_sendfile"),
        InlineKeyboardButton("« Back", callback_data="menu_main")
    )
    return markup

def get_misc_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Device ID Tool", callback_data="run_diagnostic"),
        InlineKeyboardButton("Samsung FRP", callback_data="run_samsung"),
        InlineKeyboardButton("Web USB", callback_data="run_usb"),
        InlineKeyboardButton("iPhone", callback_data="run_iphone"),
        InlineKeyboardButton("Jailbreak", callback_data="run_jailbreak"),
        InlineKeyboardButton("Text to Image", callback_data="prompt_text2image"),
        InlineKeyboardButton("Ringtone Maker", callback_data="prompt_ringtone"),
        InlineKeyboardButton("Figlet Text", callback_data="prompt_figlet"),
        InlineKeyboardButton("Kick User", callback_data="prompt_kick"),
        InlineKeyboardButton("Generate Invite", callback_data="run_invite"),
        InlineKeyboardButton("Twitter", callback_data="run_x"),
        InlineKeyboardButton("« Back", callback_data="menu_main")
    )
    return markup

# --- Inline UI Menus (FULL) ---
def main_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("ADB", callback_data="menu_adb"),
        InlineKeyboardButton("Files", callback_data="menu_files"),
        InlineKeyboardButton("Tools", callback_data="menu_tools"),
        InlineKeyboardButton("System", callback_data="menu_system"),
        InlineKeyboardButton("Admin", callback_data="menu_admin"),
    )
    return markup

def adb_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("ADB Status", callback_data="cmd_adb"),
        InlineKeyboardButton("Devices", callback_data="cmd_adb_devices"),
        InlineKeyboardButton("Bootloader", callback_data="cmd_adb_bootloader"),
        InlineKeyboardButton("Back", callback_data="back_main"),
    )
    return markup

def files_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("List Dumps", callback_data="cmd_listdumps"),
        InlineKeyboardButton("Dropzone", callback_data="cmd_dropzone"),
        InlineKeyboardButton("Send File", callback_data="cmd_sendfile"),
        InlineKeyboardButton("Back", callback_data="back_main"),
    )
    return markup

def system_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Disk Space", callback_data="cmd_diskfree"),
        InlineKeyboardButton("IP Address", callback_data="cmd_ipaddr"),
        InlineKeyboardButton("System Log", callback_data="cmd_syslog"),
        InlineKeyboardButton("Whoami", callback_data="cmd_whoami"),
        InlineKeyboardButton("LockboxPi Info", callback_data="cmd_lockboxpi"),
        InlineKeyboardButton("Back", callback_data="back_main"),
    )
    return markup

def tools_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("MTK GPT", callback_data="cmd_mtkgpt"),
        InlineKeyboardButton("MTK FRP", callback_data="cmd_mtkfrp"),
        InlineKeyboardButton("MTK Help", callback_data="cmd_mtkhelp"),
        InlineKeyboardButton("MTK Unlock", callback_data="cmd_mtkunlock"),
        InlineKeyboardButton("Knife Dump", callback_data="cmd_knifedumpr"),
        InlineKeyboardButton("Knife Key", callback_data="cmd_knifekey"),
        InlineKeyboardButton("Install APK", callback_data="cmd_installapk"),
        InlineKeyboardButton("Figlet", callback_data="cmd_figlet"),
        InlineKeyboardButton("Ringtone", callback_data="cmd_ringtone"),
        InlineKeyboardButton("Text2Image", callback_data="cmd_text2image"),
        InlineKeyboardButton("Touch Calib", callback_data="cmd_touchcalib"),
        InlineKeyboardButton("Touch Rotate", callback_data="cmd_touchrotate"),
        InlineKeyboardButton("Samsung FRP", callback_data="cmd_samsung"),
        InlineKeyboardButton("Back", callback_data="back_main"),
    )
    return markup

def admin_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Reboot", callback_data="cmd_reboot"),
        InlineKeyboardButton("Restart Bridge", callback_data="cmd_rebridge"),
        InlineKeyboardButton("Kick User", callback_data="cmd_kick"),
        InlineKeyboardButton("Invite User", callback_data="cmd_invite"),
        InlineKeyboardButton("Back", callback_data="back_main"),
    )
    return markup


# --- Handlers ---
@bot.message_handler(commands=['start', 'help', 'menu'])
def send_welcome(message):
    media_path = os.path.join(DUMPS_DIR, "trixie.gif")
    try:
        with open(media_path, 'rb') as f:
            bot.send_animation(message.chat.id, f, caption=get_header_text(), reply_markup=get_main_menu(), parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, get_header_text(), reply_markup=get_main_menu(), parse_mode="HTML")

@bot.message_handler(commands=['endpoints'])
@secure
def handle_endpoints(message):
    bot.reply_to(message, "Fetching active endpoints...")
    try:
        local_ip = subprocess.check_output(['hostname', '-I']).decode('utf-8').split()[0]
    except:
        local_ip = "127.0.0.1"
    try:
        public_ip = subprocess.check_output(['curl', '-s', 'ifconfig.me'], timeout=5).decode('utf-8').strip()
    except:
        public_ip = "Unknown"
    try:
        host_name = subprocess.check_output(['hostname']).decode('utf-8').strip()
        mdns_name = f"{host_name}.local"
    except:
        mdns_name = "lockboxpi.local"

    endpoints_text = (
        f"Public Endpoints:\n"
        f"• https://lbpi.jessejesse.com\n"
        f"• https://{public_ip}:8443\n\n"
        f"Local Endpoints:\n"
        f"• http://{mdns_name}\n"
        f"• https://{mdns_name}:8443\n"
        f"• http://{local_ip}\n"
        f"• https://{local_ip}:8443"
    )
    bot.send_message(message.chat.id, endpoints_text, disable_web_page_preview=True)

@bot.message_handler(commands=['ringtone'])
@secure
def handle_ringtone(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /ringtone [-a|-i] <url>")
        return
    do_android, do_iphone, url = True, True, ""
    for part in parts[1:]:
        if part == "-a": do_android, do_iphone = True, False
        elif part == "-i": do_android, do_iphone = False, True
        elif part.startswith("http"): url = part; break
    if not url:
        bot.reply_to(message, "Usage: /ringtone [-a|-i] <url>")
        return
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass
    msg = bot.send_message(message.chat.id, "creating ringtone...")
    total_duration = get_duration(url)
    if total_duration is None:
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text="Failed to fetch video info.")
        return
    bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text="almost complete...")
    start_time = max(0, (total_duration / 2) - 10)
    ss = f"{int(start_time // 3600):02}:{int((start_time % 3600) // 60):02}:{start_time % 60:05.2f}"
    temp_dir = os.path.join(DUMPS_DIR, f"ringtone_{message.message_id}")
    os.makedirs(temp_dir, exist_ok=True)
    mp3_path = os.path.join(temp_dir, "Ringtone-Droid.mp3")
    m4r_path = os.path.join(temp_dir, "Ringtone-Apple.m4r")
    try:
        if do_android:
            subprocess.run(['yt-dlp', '-x', '--audio-format', 'mp3', '--postprocessor-args', f'ffmpeg:-ss {ss} -t 20', '-o', mp3_path, url], check=True, capture_output=True)
        if do_iphone:
            m4a_path = os.path.join(temp_dir, "temp.m4a")
            subprocess.run(['yt-dlp', '-x', '--audio-format', 'm4a', '--postprocessor-args', f'ffmpeg:-ss {ss} -t 20', '-o', m4a_path, url], check=True, capture_output=True)
            if os.path.exists(m4a_path): os.rename(m4a_path, m4r_path)
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text="Processing complete. Uploading...")
        if do_android and os.path.exists(mp3_path):
            with open(mp3_path, 'rb') as f: bot.send_document(message.chat.id, f)
        if do_iphone and os.path.exists(m4r_path):
            with open(m4r_path, 'rb') as f: bot.send_document(message.chat.id, f)
        bot.delete_message(message.chat.id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=f"Error: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@bot.message_handler(commands=['text2image'])
@secure
def handle_text2image(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /text2image <prompt>")
        return
    prompt = parts[1]
    msg = bot.reply_to(message, f"Generating image for: {prompt}...")
    try:
        response = requests.post("https://text-to-image.jessejesse.workers.dev", json={"prompt": prompt}, timeout=60)
        if response.status_code == 200:
            bot.send_photo(message.chat.id, response.content)
            bot.delete_message(message.chat.id, msg.message_id)
        else:
            bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=f"Generation failed. Status: {response.status_code}")
    except Exception as e:
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=f"Error: {e}")

@bot.message_handler(commands=['list_dumps', 'listdumps'])
@secure
def handle_listdumps(message):
    if not os.path.exists(DUMPS_DIR):
        bot.reply_to(message, f"Directory {DUMPS_DIR} does not exist.")
        return
    files = "\n".join([f for f in os.listdir(DUMPS_DIR) if not f.startswith('.')])
    import html
    bot.reply_to(message, f"Files in dumps:\n<pre>{html.escape(files) if files else 'Directory is empty'}</pre>", parse_mode="HTML")

@bot.message_handler(commands=['send_file', 'sendfile'])
@secure
def handle_sendfile(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /sendfile <filename>")
        return
    filename = os.path.basename(parts[1])
    file_path = os.path.join(DUMPS_DIR, filename)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'rb') as f: bot.send_document(message.chat.id, f)
        except Exception as e: bot.reply_to(message, f"Error sending file: {e}")
    else: bot.reply_to(message, "File not found in dumps.")

import threading

def remote_install(ipa_path, chat_id):
    script_path = "/home/lockboxpi/alt-server/sideload.sh"
    cmd = [script_path, ipa_path]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        photo_path = os.path.join(DUMPS_DIR, "photo_AgACAgEAAyEFAATc-fVDAAIDqmm_16reTAg7XPvyQPKPqLPyiQ9MAAIFDGsbB5cBRsISTtTpTS2KAQADAgADeQADOgQ.jpg")
        try:
            with open(photo_path, 'rb') as f:
                bot.send_photo(chat_id, f)
        except Exception as e:
            pass # Suppress error if photo is missing
            
    except subprocess.CalledProcessError as e:
        full_error = (e.stdout or "") + "\n" + (e.stderr or "")
        fail_log = os.path.join(DUMPS_DIR, "sideloadfail.txt")
        try:
            with open(fail_log, 'a') as f:
                f.write(f"--- Failed sideload for {ipa_path} ---\n{full_error}\n\n")
        except Exception:
            pass
    except Exception as e:
        fail_log = os.path.join(DUMPS_DIR, "sideloadfail.txt")
        try:
            with open(fail_log, 'a') as f:
                f.write(f"--- Unknown error for {ipa_path} ---\n{str(e)}\n\n")
        except Exception:
            pass

@bot.message_handler(content_types=['document', 'photo', 'video', 'audio'])
@secure
def handle_file_upload(message):
    try:
        if message.content_type == 'document': file_id, file_name = message.document.file_id, message.document.file_name
        elif message.content_type == 'photo': file_id, file_name = message.photo[-1].file_id, f"photo_{message.photo[-1].file_id}.jpg"
        elif message.content_type == 'video': file_id, file_name = message.video.file_id, message.video.file_name or f"video_{message.video.file_id}.mp4"
        elif message.content_type == 'audio': file_id, file_name = message.audio.file_id, message.audio.file_name or f"audio_{message.audio.file_id}.mp3"
        if not file_name: file_name = f"file_{file_id}"
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_path = os.path.join(DUMPS_DIR, file_name)
        with open(file_path, 'wb') as new_file: new_file.write(downloaded_file)
        
        if file_name.lower().endswith('.ipa'):
            bot.reply_to(message, f"File '{file_name}' saved. Starting IPA installation in background...")
            threading.Thread(target=remote_install, args=(file_path, message.chat.id)).start()
        else:
            bot.reply_to(message, f"File '{file_name}' saved to dumps.")
    except Exception as e: bot.reply_to(message, f"Error saving file: {e}")

BASIC_CMDS = {'lsusb':'lsusb', 'whoami':'whoami', 'adb':'adb devices', 'adbdevices':'adb devices', 'adbbootloader':'adb reboot bootloader', 'ipaddr':'hostname -I', 'diskfree':'df -h', 'syslog':'dmesg | tail -n 30', 'x':'echo "@lightfighter719"'}
for c_n, c_e in BASIC_CMDS.items():
    @bot.message_handler(commands=[c_n])
    @secure
    def h_b(m, cmd=c_e): send_chunks(m.chat.id, run_command(cmd, shell=True))

TOOLS = {'mtkgpt':'/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py printgpt', 'mtkfrp':'/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py e frp', 'mtkhelp':'/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py -h', 'mtkgettargetconfig':'/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py gettargetconfig', 'mtkunlock':'/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py da seccfg unlock', 'mtkefrp':'/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py e frp', 'knifekey':'bash /home/lockboxpi/LockKnife/LockKnife.sh --debug', 'knifedumpr':'bash /home/lockboxpi/LockKnife/LockKnife.sh'}
for t_n, t_c in TOOLS.items():
    @bot.message_handler(commands=[t_n])
    @secure
    def h_t(m, cmd=t_c): bot.reply_to(m, f"Running: {m.text}..."); send_chunks(m.chat.id, run_command(cmd, shell=True))

MISC = {'touchrotate':'bash /home/lockboxpi/LCD-show/rotate.sh 90', 'touchcalib':'DISPLAY=:0 xinput_calibrator', 'rebridge':'sudo systemctl restart lockbox-bridge.service'}
for m_n, m_c in MISC.items():
    @bot.message_handler(commands=[m_n])
    @secure
    def h_m(m, cmd=m_c): send_chunks(m.chat.id, run_command(cmd, shell=True))

@bot.message_handler(commands=['terminal'])
@secure
def handle_terminal(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1: send_chunks(message.chat.id, run_command(parts[1], shell=True))
    else: bot.reply_to(message, "Usage: /terminal <command>")

@bot.message_handler(commands=['installapk'])
@secure
def handle_installapk(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1: send_chunks(message.chat.id, run_command(f'adb install "{parts[1]}"', shell=True))
    else: bot.reply_to(message, "Usage: /installapk <path>")

@bot.message_handler(commands=['figlet'])
@secure
def handle_figlet(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1: send_chunks(message.chat.id, run_command(f'figlet "{parts[1]}"', shell=True))
    else: bot.reply_to(message, "Usage: /figlet <text>")

@bot.message_handler(commands=['lockboxpi'])
@secure
def handle_lockboxpi(message): send_chunks(message.chat.id, run_command('fastfetch --pipe', shell=True))

@bot.message_handler(commands=['dropzone'])
@secure
def handle_dropzone(message):
    fp = os.path.join(DUMPS_DIR, "dropzone.png")
    if os.path.exists(fp):
        with open(fp, "rb") as f: bot.send_photo(message.chat.id, f)
    else: bot.reply_to(message, "dropzone.png not found.")

@bot.message_handler(commands=['kick'])
@secure
def handle_kick(message):
    parts = message.text.split(maxsplit=1)
    if message.reply_to_message: target_id, target_name = message.reply_to_message.from_user.id, message.reply_to_message.from_user.first_name
    elif len(parts) > 1 and parts[1].strip().replace('-', '').isdigit(): target_id, target_name = int(parts[1]), parts[1]
    else: bot.reply_to(message, "Reply to user or provide ID."); return
    try:
        bot.ban_chat_member(message.chat.id, target_id)
        bot.unban_chat_member(message.chat.id, target_id)
        bot.reply_to(message, f"Booted {target_name}.")
    except Exception as e: bot.reply_to(message, f"Failed: {e}")

@bot.message_handler(commands=['invite'])
@secure
def handle_invite(message):
    try:
        link = bot.create_chat_invite_link(message.chat.id, member_limit=1).invite_link
        bot.reply_to(message, f"Invite: {link}")
    except Exception as e: bot.reply_to(message, f"Failed: {e}")

@bot.message_handler(commands=['reboot'])
@secure
def handle_reboot(message): bot.reply_to(message, "Send /confirm_reboot to confirm.")

@bot.message_handler(commands=['confirm_reboot'])
@secure
def confirm_reboot(message): send_chunks(message.chat.id, run_command('sudo reboot', shell=True))

@bot.message_handler(commands=['iphone'])
@secure
def handle_iphone(message):
    file_path = os.path.join(DUMPS_DIR, 'photo_AgACAgEAAyEFAATc-fVDAAICdGm94hAa_qj_xKIVURBgA91QsA9yAAJ3C2sbJ1PxRc3x5DqiMRsWAQADAgADeQADOgQ.jpg')
    if os.path.exists(file_path):
        try:
            with open(file_path, 'rb') as f:
                bot.send_photo(message.chat.id, f)
        except Exception as e:
            bot.reply_to(message, f"Error sending image: {e}")
    else:
        bot.reply_to(message, "Image not found.")

@bot.message_handler(commands=['jailbreak'])
@secure
def handle_jailbreak(message):
    send_chunks(message.chat.id, run_command('p1f', shell=True))

@bot.message_handler(commands=['diagnostic'])
@secure
def handle_diagnostic(message):
    url = "https://device-id-bot.vercel.app/"

    # Generate QR Code in memory
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Save to a bytes buffer
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    # Setup the UI
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("I agree", url=url),
        InlineKeyboardButton("Cancel", callback_data="diag_cancel")
    )

    caption = (
        "🔗 *Diagnostic Portal*\n\n"
        "Scan this QR to run diagnostics on a separate device.\n"
        "Basic information about your device will be collected for diagnostic use only.\n\n"
        f"Link: {url}"
    )

    # Use send_photo to show the QR code with the buttons underneath
    bot.send_photo(
        message.chat.id,
        buf,
        caption=caption,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('diag_'))
def handle_diagnostic_callbacks(call):
    if call.from_user.id not in ALLOWED_USERS:
        bot.answer_callback_query(call.id, "Unauthorized")
        return

    if call.data == "diag_cancel":
        bot.answer_callback_query(call.id)
        # For photos, we delete the message instead of editing text
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "Canceled.")
@bot.message_handler(func=lambda message: message.text and "🚨 New Diagnostic Report 🚨" in message.text)
@secure
def save_incoming_diagnostic(message):
    try:
        report_id = "unknown"
        for line in message.text.split('\n'):
            if line.startswith("ID: "):
                report_id = line.replace("ID: ", "").strip()
                break
        
        filepath = os.path.join(DUMPS_DIR, f"{report_id}.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(message.text)
            
        bot.reply_to(message, f"✅ Saved diagnostic report to /dumps/{report_id}.txt")
    except Exception as e:
        bot.reply_to(message, f"❌ Error saving report: {e}")

@bot.message_handler(commands=['samsung'])
@secure
def handle_samsung(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("1. plugged in", callback_data="sam_plugged"), InlineKeyboardButton("2. cancel", callback_data="sam_cancel"))
    bot.reply_to(message, "Plug device in to computer USB", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('sam_'))
def handle_samsung_callbacks(call):
    if call.from_user.id not in ALLOWED_USERS: bot.answer_callback_query(call.id, "Unauthorized"); return
    bot.answer_callback_query(call.id)
    if call.data == "sam_cancel": bot.edit_message_text("Canceled.", call.message.chat.id, call.message.message_id)
    elif call.data == "sam_plugged":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("I am using Chrome", callback_data="sam_chrome"), InlineKeyboardButton("2. cancel", callback_data="sam_cancel"))
        bot.edit_message_text("open https://lbpi.jessejesse.com/dumps/frp.html\n\n<b>Chrome only!</b>", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
    elif call.data == "sam_chrome":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("1. initialized", callback_data="sam_init"), InlineKeyboardButton("2. cancel", callback_data="sam_cancel"))
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            p1 = os.path.join(DUMPS_DIR, 'photo_AgACAgEAAxkBAAIB5Wm6GTFsc9dOJdBfI0ONn1fIm3H2AAIkDGsbf1_QRZ9-wWhLzPqSAQADAgADeQADOgQ.jpg')
            with open(p1, 'rb') as f: bot.send_photo(call.message.chat.id, f, caption="Select 'initialize port'", reply_markup=markup)
        except: bot.send_message(call.message.chat.id, "Select 'initialize port'", reply_markup=markup)
    elif call.data == "sam_init":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            p2 = os.path.join(DUMPS_DIR, 'photo_AgACAgEAAxkBAAIB52m6GTp9pjC4-YQnUbxzqjb9DMpBAAIlDGsbf1_QRYQfj61bd7QAAQEAAwIAA3kAAzoE.jpg')
            with open(p2, 'rb') as f: bot.send_photo(call.message.chat.id, f, caption="Follow sequence, then handshake.")
        except: bot.send_message(call.message.chat.id, "Follow sequence, then handshake.")

@bot.message_handler(commands=['usb'])
@secure
def handle_usb(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("1. is usb connected", callback_data="usb_connected"), InlineKeyboardButton("2. cancel", callback_data="usb_cancel"))
    bot.reply_to(message, "USB Connection Required", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('usb_'))
def handle_usb_callbacks(call):
    if call.from_user.id not in ALLOWED_USERS: bot.answer_callback_query(call.id, "Unauthorized"); return
    bot.answer_callback_query(call.id)
    if call.data == "usb_cancel":
        bot.edit_message_text("Canceled.", call.message.chat.id, call.message.message_id)
    elif call.data == "usb_connected":
        bot.edit_message_text("https://webusb-chrome.vercel.app\n\n<b>*must be chrome browser</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML")

# --- UI Prompt Step Handlers ---
def process_terminal_step(message):
    if not message.text: return
    message.text = f"/terminal {message.text}"
    handle_terminal(message)

def process_installapk_step(message):
    if not message.text: return
    message.text = f"/installapk {message.text}"
    handle_installapk(message)

def process_sendfile_step(message):
    if not message.text: return
    message.text = f"/sendfile {message.text}"
    handle_sendfile(message)

def process_text2image_step(message):
    if not message.text: return
    message.text = f"/text2image {message.text}"
    handle_text2image(message)

def process_ringtone_step(message):
    if not message.text: return
    message.text = f"/ringtone {message.text}"
    handle_ringtone(message)

def process_figlet_step(message):
    if not message.text: return
    message.text = f"/figlet {message.text}"
    handle_figlet(message)

def process_kick_step(message):
    if not message.text: return
    message.text = f"/kick {message.text}"
    handle_kick(message)

# --- Master UI Callback Handler ---
@bot.callback_query_handler(func=lambda call: call.data.startswith(('menu_', 'run_', 'prompt_')))
def handle_ui_callbacks(call):
    user_ok = (len(ALLOWED_USERS) == 0) or (call.from_user.id in ALLOWED_USERS)
    chat_ok = (CHAT_ID == 0) or (call.message.chat.id == CHAT_ID)
    if not (user_ok and chat_ok):
        bot.answer_callback_query(call.id, "Unauthorized")
        return

    data = call.data

    if data.startswith("menu_"):
        bot.answer_callback_query(call.id)
        if data == "menu_main":
            bot.edit_message_caption(get_header_text(), call.message.chat.id, call.message.message_id, reply_markup=get_main_menu(), parse_mode="HTML")
        elif data == "menu_adb":
            bot.edit_message_caption(f"{get_header_text()}\n\n<b>ADB & Device Tools</b>", call.message.chat.id, call.message.message_id, reply_markup=get_adb_menu(), parse_mode="HTML")
        elif data == "menu_mtk":
            bot.edit_message_caption(f"{get_header_text()}\n\n<b>MTK Tools</b>", call.message.chat.id, call.message.message_id, reply_markup=get_mtk_menu(), parse_mode="HTML")
        elif data == "menu_knife":
            bot.edit_message_caption(f"{get_header_text()}\n\n<b>LockKnife Tools</b>", call.message.chat.id, call.message.message_id, reply_markup=get_knife_menu(), parse_mode="HTML")
        elif data == "menu_system":
            bot.edit_message_caption(f"{get_header_text()}\n\n<b>System & Pi Info</b>", call.message.chat.id, call.message.message_id, reply_markup=get_system_menu(), parse_mode="HTML")
        elif data == "menu_files":
            bot.edit_message_caption(f"{get_header_text()}\n\n<b>Files & Dumps</b>", call.message.chat.id, call.message.message_id, reply_markup=get_files_menu(), parse_mode="HTML")
        elif data == "menu_misc":
            bot.edit_message_caption(f"{get_header_text()}\n\n<b>Media & Misc</b>", call.message.chat.id, call.message.message_id, reply_markup=get_misc_menu(), parse_mode="HTML")
        elif data == "menu_close":
            bot.delete_message(call.message.chat.id, call.message.message_id)
        return

    if data.startswith("prompt_"):
        cmd_name = data.split("_")[1]
        bot.answer_callback_query(call.id)
        if cmd_name == "terminal":
            msg = bot.send_message(call.message.chat.id, "Please enter the shell command to execute:")
            bot.register_next_step_handler(msg, process_terminal_step)
        elif cmd_name == "installapk":
            msg = bot.send_message(call.message.chat.id, "Please provide the path or URL of the APK:")
            bot.register_next_step_handler(msg, process_installapk_step)
        elif cmd_name == "sendfile":
            msg = bot.send_message(call.message.chat.id, "Please enter the exact filename to send from the dumps directory:")
            bot.register_next_step_handler(msg, process_sendfile_step)
        elif cmd_name == "text2image":
            msg = bot.send_message(call.message.chat.id, "Please enter a detailed prompt for the image generation:")
            bot.register_next_step_handler(msg, process_text2image_step)
        elif cmd_name == "ringtone":
            msg = bot.send_message(call.message.chat.id, "Please provide the video URL to process:")
            bot.register_next_step_handler(msg, process_ringtone_step)
        elif cmd_name == "figlet":
            msg = bot.send_message(call.message.chat.id, "Please enter the text to convert to ASCII art:")
            bot.register_next_step_handler(msg, process_figlet_step)
        elif cmd_name == "kick":
            msg = bot.send_message(call.message.chat.id, "Please provide the User ID to kick from the group:")
            bot.register_next_step_handler(msg, process_kick_step)
        return

    if data.startswith("run_"):
        cmd_name = data.split("_", 1)[1]
        bot.answer_callback_query(call.id, f"Executing {cmd_name}...")
        
        # Prepare mock message to pass to handlers
        call.message.from_user = call.from_user
        call.message.text = f"/{cmd_name}"
        
        cmd_str = None
        if cmd_name in BASIC_CMDS: cmd_str = BASIC_CMDS[cmd_name]
        elif cmd_name in TOOLS: cmd_str = TOOLS[cmd_name]
        elif cmd_name in MISC: cmd_str = MISC[cmd_name]
            
        if cmd_str:
            bot.send_message(call.message.chat.id, f"Executing <code>/{cmd_name}</code>...", parse_mode="HTML")
            send_chunks(call.message.chat.id, run_command(cmd_str, shell=True))
            return
            
        if cmd_name == "endpoints": handle_endpoints(call.message)
        elif cmd_name == "lockboxpi": handle_lockboxpi(call.message)
        elif cmd_name == "listdumps": handle_listdumps(call.message)
        elif cmd_name == "dropzone": handle_dropzone(call.message)
        elif cmd_name == "reboot": handle_reboot(call.message)
        elif cmd_name == "invite": handle_invite(call.message)
        elif cmd_name == "samsung": handle_samsung(call.message)
        elif cmd_name == "diagnostic": handle_diagnostic(call.message)
        elif cmd_name == "usb": handle_usb(call.message)
        elif cmd_name == "iphone": handle_iphone(call.message)
        elif cmd_name == "jailbreak": handle_jailbreak(call.message)
        return

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

if __name__ == '__main__':
    cmds = sorted([BotCommand(k, v) for k, v in COMMAND_DESCRIPTIONS.items()], key=lambda x: x.command)
    try: bot.set_my_commands(cmds)
    except: pass
    print("Bot starting..."); bot.remove_webhook(); bot.polling(none_stop=True)
