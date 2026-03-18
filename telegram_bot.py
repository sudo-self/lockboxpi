import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import subprocess
import os
import shlex
import logging

# --- Configuration ---
TOKEN = '8698638609:AAEaE1oKl1307vB11rOK_RoDniiAm2BeELY'
ALLOWED_USERS = [7251722622]
DUMPS_DIR = '/var/www/dumps'
OUTPUT_LIMIT = 3500  # characters for stdout
ERROR_LIMIT = 500    # characters for stderr
TIMEOUT = 120        # seconds

bot = telebot.TeleBot(TOKEN)

# --- Logging ---
logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# --- Helpers ---
def is_allowed(message):
    return message.from_user.id in ALLOWED_USERS

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
            if message.chat.type not in ["group", "supergroup"]:
                bot.reply_to(message, "Unauthorized")
            logging.warning(f"Unauthorized access attempt by {message.from_user.id}")
            return
        return handler(message)
    return wrapper

def send_chunks(chat_id, text):
    """Send long text in multiple messages if needed"""
    for i in range(0, len(text), 4000):
        bot.send_message(chat_id, f"```text\n{text[i:i+4000]}\n```", parse_mode="Markdown")

# --- Handlers ---
@bot.message_handler(commands=['start', 'help', 'commands'])
def send_welcome(message):
    help_text = (
        "💡 *Upload Files:* Send any file, photo, or video to this chat to upload it to the dumps folder.\n\n"
        "commands - Lists commands\n"
        "lsusb - Lists connected USB devices\n"
        "whoami - Shows current user info\n"
        "adb - Checks ADB connection status\n"
        "adb_devices - Lists connected ADB devices\n"
        "adb_bootloader - Reboots device to bootloader\n"
        "ip_addr - Displays IP address\n"
        "disk_free - Shows free disk space\n"
        "mtk_help - Shows MTK Client help\n"
        "mtk_gpt - Dumps MTK GPT partition table\n"
        "mtk_gettargetconfig - Gets MTK target config\n"
        "mtk_frp - Manages MTK FRP operations\n"
        "mtk_unlock - Unlocks MTK device via seccfg\n"
        "mtk_e_frp - Erases MTK FRP partition\n"
        "knife_key - Extracts keys via Knife\n"
        "knife_dumpr - Dumps partitions via Knife\n"
        "list_dumps - Lists files in dumps folder\n"
        "send_file - Sends a file from dumps\n"
        "sys_log - Shows the system log\n"
        "reboot - Reboots the device\n"
        "terminal - Runs a shell command\n"
        "touch_rotate - Rotates touch orientation\n"
        "touch_calib - Calibrates the touchscreen\n"
        "re_bridge - Restarts bridge connection\n"
        "install_apk - Installs an APK\n"
        "samsung - Interactive Samsung FRP flow"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

# --- File Management ---
@bot.message_handler(commands=['list_dumps'])
@secure
def handle_list_dumps(message):
    if not os.path.exists(DUMPS_DIR):
        bot.reply_to(message, f"Directory {DUMPS_DIR} does not exist.")
        return
    files = "\n".join(os.listdir(DUMPS_DIR))
    bot.reply_to(message, f"Files in dumps:\n```{files if files else 'Directory is empty'}```", parse_mode="Markdown")

@bot.message_handler(commands=['send_file'])
@secure
def handle_send_file(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /send_file <filename>")
        return
    filename = os.path.basename(parts[1])  # sanitize input
    file_path = os.path.join(DUMPS_DIR, filename)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'rb') as f:
                bot.send_document(message.chat.id, f)
        except Exception as e:
            bot.reply_to(message, f"Error sending file: {e}")
    else:
        bot.reply_to(message, "File not found in dumps.")

@bot.message_handler(content_types=['document', 'photo', 'video', 'audio'])
@secure
def handle_file_upload(message):
    try:
        if message.content_type == 'document':
            file_id = message.document.file_id
            file_name = message.document.file_name
        elif message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            file_name = f"photo_{file_id}.jpg"
        elif message.content_type == 'video':
            file_id = message.video.file_id
            file_name = message.video.file_name or f"video_{file_id}.mp4"
        elif message.content_type == 'audio':
            file_id = message.audio.file_id
            file_name = message.audio.file_name or f"audio_{file_id}.mp3"

        if not file_name:
            file_name = f"file_{file_id}"

        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        file_path = os.path.join(DUMPS_DIR, file_name)
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        bot.reply_to(message, f"✅ File '{file_name}' saved to dumps folder.")
        logging.info(f"{message.from_user.id} uploaded file: {file_name}")
    except Exception as e:
        bot.reply_to(message, f"❌ Error saving file: {e}")
        logging.error(f"Error saving uploaded file: {e}")

# --- Basic & System Commands ---
BASIC_CMDS = {
    'lsusb': 'lsusb',
    'whoami': 'whoami',
    'adb': 'adb devices',
    'adb_devices': 'adb devices',
    'adb_bootloader': 'adb reboot bootloader',
    'ip_addr': 'hostname -I',
    'disk_free': 'df -h',
    'sys_log': 'dmesg | tail -n 30'
}

for cmd_name, cmd_exec in BASIC_CMDS.items():
    @bot.message_handler(commands=[cmd_name])
    @secure
    def handle_basic(message, cmd=cmd_exec):
        logging.info(f"{message.from_user.id} ran {message.text}")
        send_chunks(message.chat.id, run_command(cmd, shell=True))

# --- Tools ---
TOOLS = {
    'mtk_gpt': '/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py printgpt',
    'mtk_frp': '/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py e frp',
    'mtk_help': '/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py -h',
    'mtk_gettargetconfig': '/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py gettargetconfig',
    'mtk_unlock': '/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py da seccfg unlock',
    'mtk_e_frp': '/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py e frp',
    'knife_key': 'bash /home/lockboxpi/LockKnife/LockKnife.sh --debug',
    'knife_dumpr': 'bash /home/lockboxpi/LockKnife/LockKnife.sh'
}

for tool_name, tool_cmd in TOOLS.items():
    @bot.message_handler(commands=[tool_name])
    @secure
    def handle_tools(message, cmd=tool_cmd):
        logging.info(f"{message.from_user.id} ran {message.text}")
        bot.reply_to(message, f"Running: {message.text}...")
        send_chunks(message.chat.id, run_command(cmd, shell=True))

# --- Misc ---
MISC_CMDS = {
    'touch_rotate': 'bash /home/lockboxpi/LCD-show/rotate.sh 90',
    'touch_calib': 'DISPLAY=:0 xinput_calibrator',
    're_bridge': 'sudo systemctl restart lockbox-bridge.service'
}

for misc_name, misc_cmd in MISC_CMDS.items():
    @bot.message_handler(commands=[misc_name])
    @secure
    def handle_misc(message, cmd=misc_cmd):
        logging.info(f"{message.from_user.id} ran {message.text}")
        send_chunks(message.chat.id, run_command(cmd, shell=True))

# --- Terminal ---
@bot.message_handler(commands=['terminal'])
@secure
def handle_terminal(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        logging.info(f"{message.from_user.id} ran terminal command: {parts[1]}")
        send_chunks(message.chat.id, run_command(parts[1], shell=True))
    else:
        bot.reply_to(message, "Usage: /terminal <command>")

# --- Install APK ---
@bot.message_handler(commands=['install_apk'])
@secure
def handle_install_apk(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        cmd = f'adb install "{parts[1]}"'
        logging.info(f"{message.from_user.id} installing APK: {parts[1]}")
        send_chunks(message.chat.id, run_command(cmd, shell=True))
    else:
        bot.reply_to(message, "Usage: /install_apk <path_to_apk>")

# --- Reboot with confirmation ---
@bot.message_handler(commands=['reboot'])
@secure
def handle_reboot(message):
    bot.reply_to(message, "⚠️ Confirm reboot by sending: /confirm_reboot")

@bot.message_handler(commands=['confirm_reboot'])
@secure
def confirm_reboot(message):
    logging.info(f"{message.from_user.id} confirmed reboot")
    send_chunks(message.chat.id, run_command('sudo reboot', shell=True))

# --- Samsung Interactive Flow ---
@bot.message_handler(commands=['samsung'])
@secure
def handle_samsung(message):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("1. plugged in", callback_data="sam_plugged"),
        InlineKeyboardButton("2. cancel", callback_data="sam_cancel")
    )
    bot.reply_to(message, "Plug device in to computer USB", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('sam_'))
def handle_samsung_callbacks(call):
    # Ensure the user who clicked the button is allowed
    if call.from_user.id not in ALLOWED_USERS:
        bot.answer_callback_query(call.id, "Unauthorized")
        return

    bot.answer_callback_query(call.id)  # Acknowledge the callback

    if call.data == "sam_cancel":
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Canceled.")

    elif call.data == "sam_plugged":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("1. open in chrome", callback_data="sam_chrome"),
            InlineKeyboardButton("2. cancel", callback_data="sam_cancel")
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text="once device is connected open [Samsung FRP](https://73.243.235.226/dumps/frp.html)", reply_markup=markup, parse_mode="Markdown")

    elif call.data == "sam_chrome":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("1. initialized", callback_data="sam_init"),
            InlineKeyboardButton("2. cancel", callback_data="sam_cancel")
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text="select the white button 'initialize port'", reply_markup=markup)

    elif call.data == "sam_init":
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text="press the sequence buttons in order then repeact steps for interface 02.")

# --- Main ---
if __name__ == '__main__':
    print("Bot is starting... Press Ctrl+C to stop.")
    bot.polling(none_stop=True)
