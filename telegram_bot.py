import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import subprocess
import os
import shlex
import logging

# --- Configuration ---
# Sensative info should be set as environment variables or in a local .env file
# Example .env file content:
# BOT_TOKEN=your_token_here
# ALLOWED_USERS=12345678,98765432
TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ALLOWED_USERS_RAW = os.getenv('ALLOWED_USERS', '0')
ALLOWED_USERS = [int(u.strip()) for u in ALLOWED_USERS_RAW.split(',') if u.strip().replace('-', '').isdigit()]
CHAT_ID_RAW = os.getenv('CHAT_ID', '0')
CHAT_ID = int(CHAT_ID_RAW.strip()) if CHAT_ID_RAW.strip().replace('-', '').isdigit() else 0
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
    user_ok = message.from_user.id in ALLOWED_USERS
    # If CHAT_ID is 0, allow from any chat (where user is authorized).
    # If CHAT_ID is set, only allow from that specific chat ID.
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
    """Send long text in multiple messages if needed"""
    for i in range(0, len(text), 4000):
        bot.send_message(chat_id, f"```text\n{text[i:i+4000]}\n```", parse_mode="Markdown")

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
@bot.message_handler(commands=['start', 'help', 'commands'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "LockboxPi Control Panel\n\nSelect a category:",
        reply_markup=main_menu()
    )

# --- File Management ---
@bot.message_handler(commands=['list_dumps', 'listdumps'])
@secure
def handle_listdumps(message):
    if not os.path.exists(DUMPS_DIR):
        bot.reply_to(message, f"Directory {DUMPS_DIR} does not exist.")
        return
    files = "\n".join([f for f in os.listdir(DUMPS_DIR) if not f.startswith('.')])
    bot.reply_to(message, f"Files in dumps:\n```{files if files else 'Directory is empty'}```", parse_mode="Markdown")

@bot.message_handler(commands=['send_file', 'sendfile'])
@secure
def handle_sendfile(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /sendfile <filename>")
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
    'adbdevices': 'adb devices',
    'adb_bootloader': 'adb reboot bootloader',
    'adbbootloader': 'adb reboot bootloader',
    'ip_addr': 'hostname -I',
    'ipaddr': 'hostname -I',
    'disk_free': 'df -h',
    'diskfree': 'df -h',
    'sys_log': 'dmesg | tail -n 30',
    'syslog': 'dmesg | tail -n 30',
    'x': 'echo "@lightfighter719"'
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
    'mtkgpt': '/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py printgpt',
    'mtk_frp': '/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py e frp',
    'mtkfrp': '/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py e frp',
    'mtk_help': '/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py -h',
    'mtkhelp': '/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py -h',
    'mtk_gettargetconfig': '/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py gettargetconfig',
    'mtkgettargetconfig': '/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py gettargetconfig',
    'mtk_unlock': '/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py da seccfg unlock',
    'mtkunlock': '/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py da seccfg unlock',
    'mtk_e_frp': '/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py e frp',
    'mtkefrp': '/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py e frp',
    'knife_key': 'bash /home/lockboxpi/LockKnife/LockKnife.sh --debug',
    'knifekey': 'bash /home/lockboxpi/LockKnife/LockKnife.sh --debug',
    'knife_dumpr': 'bash /home/lockboxpi/LockKnife/LockKnife.sh',
    'knifedumpr': 'bash /home/lockboxpi/LockKnife/LockKnife.sh'
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
    'touchrotate': 'bash /home/lockboxpi/LCD-show/rotate.sh 90',
    'touch_calib': 'DISPLAY=:0 xinput_calibrator',
    'touchcalib': 'DISPLAY=:0 xinput_calibrator',
    're_bridge': 'sudo systemctl restart lockbox-bridge.service',
    'rebridge': 'sudo systemctl restart lockbox-bridge.service'
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
@bot.message_handler(commands=['install_apk', 'installapk'])
@secure
def handle_installapk(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        cmd = f'adb install "{parts[1]}"'
        logging.info(f"{message.from_user.id} installing APK: {parts[1]}")
        send_chunks(message.chat.id, run_command(cmd, shell=True))
    else:
        bot.reply_to(message, "Usage: /installapk <path_to_apk>")

# --- Figlet ---
@bot.message_handler(commands=['figlet'])
@secure
def handle_figlet(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        text = parts[1]
        logging.info(f"{message.from_user.id} ran figlet: {text}")
        output = run_command(f'figlet "{text}"', shell=True)
        send_chunks(message.chat.id, output)
    else:
        bot.reply_to(message, "Usage: /figlet <text>")

# --- LockboxPi Stats ---
@bot.message_handler(commands=['lockboxpi'])
@secure
def handle_lockboxpi(message):
    logging.info(f"{message.from_user.id} ran lockboxpi (fastfetch)")
    # Use --pipe for plain output suitable for Telegram
    output = run_command('fastfetch --pipe', shell=True)
    send_chunks(message.chat.id, output)

@bot.message_handler(commands=["dropzone"])
@secure
def handle_dropzone(message):
    file_path = os.path.join(DUMPS_DIR, "dropzone.png")
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                bot.send_photo(message.chat.id, f)
        except Exception as e:
            bot.reply_to(message, f"Error sending photo: {e}")
    else:
        bot.reply_to(message, "dropzone.png not found in dumps.")

# --- Kick User ---
@bot.message_handler(commands=['kick'])
@secure
def handle_kick(message):
    parts = message.text.split(maxsplit=1)
    
    # Kick by replying to a message
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.first_name
    # Kick by providing a numeric user ID
    elif len(parts) > 1 and parts[1].strip().replace('-', '').isdigit():
        target_id = int(parts[1].strip())
        target_name = parts[1].strip()
    # Attempting to kick by @username
    elif len(parts) > 1:
        bot.reply_to(message, "⚠️ **Telegram API Limitation:** Bots cannot kick by `@username` directly.\n\nPlease either:\n1. **Reply** to one of their messages with `/kick`\n2. Provide their numeric User ID: `/kick 123456789`", parse_mode="Markdown")
        return
    else:
        bot.reply_to(message, "Usage:\n- Reply to their message with `/kick`\n- Or use `/kick <user_id>`", parse_mode="Markdown")
        return

    try:
        # Ban and immediately unban to remove them from the group without a permanent ban
        bot.ban_chat_member(message.chat.id, target_id)
        bot.unban_chat_member(message.chat.id, target_id)
        bot.reply_to(message, f"👢 Successfully kicked {target_name}.")
    except Exception as e:
        bot.reply_to(message, f"❌ Failed to kick. Make sure I am an admin and the target is not an admin.\n`{e}`", parse_mode="Markdown")

# --- Invite User ---
@bot.message_handler(commands=['invite'])
@secure
def handle_invite(message):
    try:
        # Generate a one-time use invite link for the current chat
        invite_link = bot.create_chat_invite_link(message.chat.id, member_limit=1).invite_link
        bot.reply_to(message, f"🔗 Here is a one-time invite link:\n{invite_link}")
    except Exception as e:
        bot.reply_to(message, f"❌ Failed to generate invite link. Make sure I am an admin with the 'Invite Users' permission.\n`{e}`", parse_mode="Markdown")

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
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, "Canceled.")
        except Exception:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Canceled.")

    elif call.data == "sam_plugged":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("I am using Chrome", callback_data="sam_chrome"),
            InlineKeyboardButton("2. cancel", callback_data="sam_cancel")
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text="once device is connected open https://lbpi.jessejesse.com/dumps/frp.html\n\n⚠️ **STOP! must be chrome browser!**", 
                              reply_markup=markup, parse_mode="Markdown")

    elif call.data == "sam_chrome":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("1. initialized", callback_data="sam_init"),
            InlineKeyboardButton("2. cancel", callback_data="sam_cancel")
        )
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            photo1_path = os.path.join(DUMPS_DIR, 'photo_AgACAgEAAxkBAAIB5Wm6GTFsc9dOJdBfI0ONn1fIm3H2AAIkDGsbf1_QRZ9-wWhLzPqSAQADAgADeQADOgQ.jpg')
            with open(photo1_path, 'rb') as photo:
                bot.send_photo(call.message.chat.id, photo, 
                               caption="open https://lbpi.jessejesse.com/dumps/frp.html\n\nselect the white button 'initialize port'", 
                               reply_markup=markup)
        except Exception as e:
            logging.error(f"Error sending samsung photo1: {e}")
            bot.send_message(call.message.chat.id, "open https://lbpi.jessejesse.com/dumps/frp.html\n\nselect the white button 'initialize port'", reply_markup=markup)

    elif call.data == "sam_init":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            photo2_path = os.path.join(DUMPS_DIR, 'photo_AgACAgEAAxkBAAIB52m6GTp9pjC4-YQnUbxzqjb9DMpBAAIlDGsbf1_QRYQfj61bd7QAAQEAAwIAA3kAAzoE.jpg')
            with open(photo2_path, 'rb') as photo:
                bot.send_photo(call.message.chat.id, photo, 
                               caption="press the sequence buttons in order, leave the divice connected and select the white initilize handshake button\n\nThanks for using samsung remote frp service @lockboxtrixie_bot")
        except Exception as e:
            logging.error(f"Error sending samsung photo2: {e}")
            bot.send_message(call.message.chat.id, "press the sequence buttons in order, leave the divice connected and select the white initilize handshake button\n\nThanks for using samsung remote frp service @lockboxtrixie_bot")


# --- Inline UI Callback Router ---
@bot.callback_query_handler(func=lambda call: call.data.startswith(("menu_", "cmd_", "back_")))
def handle_menu_callbacks(call):
    if call.from_user.id not in ALLOWED_USERS:
        bot.answer_callback_query(call.id, "Unauthorized")
        return

    bot.answer_callback_query(call.id)

    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    # Navigation menus
    if call.data == "menu_adb":
        bot.edit_message_text("ADB Menu", chat_id, msg_id, reply_markup=adb_menu())
    elif call.data == "menu_files":
        bot.edit_message_text("File Menu", chat_id, msg_id, reply_markup=files_menu())
    elif call.data == "menu_system":
        bot.edit_message_text("System Menu", chat_id, msg_id, reply_markup=system_menu())
    elif call.data == "menu_tools":
        bot.edit_message_text("Tools Menu", chat_id, msg_id, reply_markup=tools_menu())
    elif call.data == "menu_admin":
        bot.edit_message_text("Admin Menu", chat_id, msg_id, reply_markup=admin_menu())
    elif call.data == "back_main":
        bot.edit_message_text("Main Menu", chat_id, msg_id, reply_markup=main_menu())

    # Command execution via buttons
    elif call.data.startswith("cmd_"):
        command = call.data.replace("cmd_", "")
        # Construct a fake message to trigger your normal command handlers
        fake_message = call.message
        fake_message.chat = call.message.chat
        fake_message.from_user = call.from_user
        fake_message.text = f"/{command}"
        bot.process_new_messages([fake_message])

    # Navigation
    if call.data == "menu_adb":
        bot.edit_message_text("ADB Menu", chat_id, msg_id, reply_markup=adb_menu())

    elif call.data == "menu_files":
        bot.edit_message_text("File Menu", chat_id, msg_id, reply_markup=files_menu())

    elif call.data == "menu_system":
        bot.edit_message_text("System Menu", chat_id, msg_id, reply_markup=system_menu())

    elif call.data == "menu_tools":
        bot.edit_message_text("Tools Menu", chat_id, msg_id, reply_markup=tools_menu())

    elif call.data == "menu_admin":
        bot.edit_message_text("Admin Menu", chat_id, msg_id, reply_markup=admin_menu())

    elif call.data == "back_main":
        bot.edit_message_text("Main Menu", chat_id, msg_id, reply_markup=main_menu())

   # Command execution
elif call.data.startswith("cmd_"):
    command = call.data.replace("cmd_", "")

    fake_message = call.message
    fake_message.chat = call.message.chat
    fake_message.from_user = call.from_user
    fake_message.text = f"/{command}"

    bot.process_new_messages([fake_message])
# --- Main ---
if __name__ == '__main__':
    from telebot.types import BotCommand
    commands = [
        BotCommand("adb", "Checks ADB connection status"),
        BotCommand("disk_free", "Shows free disk space"),
        BotCommand("dropzone", "display dropzone"),
        BotCommand("figlet", "Prints text in ASCII art"),
        BotCommand("help", "Show help message"),
        BotCommand("install_apk", "Installs an APK"),
        BotCommand("invite", "Generates a one-time invite link"),
        BotCommand("ip_addr", "Displays IP address"),
        BotCommand("kick", "Kicks a user from the group"),
        BotCommand("knife_dumpr", "Dumps partitions via Knife"),
        BotCommand("knife_key", "Extracts keys via Knife"),
        BotCommand("list_dumps", "Lists files in dumps folder"),
        BotCommand("lockboxpi", "Shows system info via fastfetch"),
        BotCommand("lsusb", "List USB devices"),
        BotCommand("mtk_frp", "Manages MTK FRP operations"),
        BotCommand("mtk_gpt", "Dumps MTK GPT partition table"),
        BotCommand("re_bridge", "Restarts bridge connection"),
        BotCommand("reboot", "Reboots the device"),
        BotCommand("samsung", "Interactive Samsung FRP flow"),
        BotCommand("send_file", "Sends a file from dumps"),
        BotCommand("start", "Show help message"),
        BotCommand("sys_log", "Shows the system log"),
        BotCommand("terminal", "Runs a shell command"),
        BotCommand("touch_calib", "Calibrates the touchscreen"),
        BotCommand("touch_rotate", "Rotates touch orientation"),
        BotCommand("whoami", "Show current user info"),
    ]
    try:
        bot.set_my_commands(commands)
    except Exception as e:
        print(f'Failed to set commands: {e}')

    print("Bot is starting... Press Ctrl+C to stop.")
    bot.polling(none_stop=True)
