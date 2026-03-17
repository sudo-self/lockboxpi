import telebot
import subprocess

TOKEN = '8698638609:AAEaE1oKl1307vB11rOK_RoDniiAm2BeELY'
ALLOWED_USERS = [7251722622]

bot = telebot.TeleBot(TOKEN)

def is_allowed(message):
    return message.from_user.id in ALLOWED_USERS

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        output = result.stdout
        error = result.stderr

        response = ""
        if output:
            response += f"Output:\n{output[:3500]}\n"
        if error:
            response += f"Error:\n{error[:500]}\n"

        if not response:
            response = "Command executed successfully with no output."

        return response
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as e:
        return f"Exception occurred: {str(e)}"


def secure(handler):
    def wrapper(message):
        # Only allow YOU to execute commands
        if not is_allowed(message):
            # In groups → ignore silently
            if message.chat.type in ["group", "supergroup"]:
                return
            # In private → show unauthorized
            else:
                bot.reply_to(message, "Unauthorized")
                return

        return handler(message)
    return wrapper


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    help_text = (
        "Trixie Bot can run commands on pi.\n\n"
        "\n\n"
        "lbpi.JesseJesse.com\n\n"
        "/lsusb - List USB devices\n"
        "/whoami - Show current user\n"
        "/adb - Show connected ADB devices\n"
        "/mtk_gpt - Run MTK PrintGPT\n"
        "/mtk_frp - Run MTK FRP Erase\n"
        "/knife_key - Run LockKnife Key Extraction\n"
        "/knife_dumpr - Run LockKnife Dump\n"
        "/ip_addr - Show IP Address\n"
        "/disk_free - Show Free Disk Space\n"
        "/sys_log - Show System Log (dmesg)\n"
        "/touch_rotate - Rotate Touchscreen\n"
        "/touch_calib - Calibrate Touchscreen\n"
        "/install_apk - Install an APK\n"
        "/re_bridge - Restart Bridge Script\n"
        "/reboot - Reboot the System\n"
        "/terminal - Execute commands"
    )
    bot.reply_to(message, help_text)


# Basic Commands
@bot.message_handler(commands=['lsusb'])
@secure
def handle_lsusb(message):
    bot.reply_to(message, f"```text\n{run_command('lsusb')}\n```", parse_mode="Markdown")


@bot.message_handler(commands=['whoami'])
@secure
def handle_whoami(message):
    bot.reply_to(message, f"```text\n{run_command('whoami')}\n```", parse_mode="Markdown")


@bot.message_handler(commands=['adb'])
@secure
def handle_adb(message):
    bot.reply_to(message, f"```text\n{run_command('adb devices')}\n```", parse_mode="Markdown")


# MTK Commands
@bot.message_handler(commands=['mtk_gpt'])
@secure
def handle_mtk_gpt(message):
    bot.reply_to(message, "Running MTK PrintGPT...")
    bot.reply_to(message, f"```text\n{run_command('/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py printgpt')}\n```", parse_mode="Markdown")


@bot.message_handler(commands=['mtk_frp'])
@secure
def handle_mtk_frp(message):
    bot.reply_to(message, "Erasing FRP...")
    bot.reply_to(message, f"```text\n{run_command('/home/lockboxpi/mtk_env/bin/python3 /home/lockboxpi/mtkclient/mtk.py e frp')}\n```", parse_mode="Markdown")


# LockKnife
@bot.message_handler(commands=['knife_key'])
@secure
def handle_knife_key(message):
    bot.reply_to(message, f"```text\n{run_command('bash /home/lockboxpi/LockKnife/LockKnife.sh --debug')}\n```", parse_mode="Markdown")


@bot.message_handler(commands=['knife_dumpr'])
@secure
def handle_knife_dumpr(message):
    bot.reply_to(message, f"```text\n{run_command('bash /home/lockboxpi/LockKnife/LockKnife.sh')}\n```", parse_mode="Markdown")


# System
@bot.message_handler(commands=['ip_addr'])
@secure
def handle_ip_addr(message):
    bot.reply_to(message, f"```text\n{run_command('hostname -I')}\n```", parse_mode="Markdown")


@bot.message_handler(commands=['disk_free'])
@secure
def handle_disk_free(message):
    bot.reply_to(message, f"```text\n{run_command('df -h')}\n```", parse_mode="Markdown")


@bot.message_handler(commands=['sys_log'])
@secure
def handle_sys_log(message):
    bot.reply_to(message, f"```text\n{run_command('dmesg | tail -n 30')}\n```", parse_mode="Markdown")


@bot.message_handler(commands=['touch_rotate'])
@secure
def handle_touch_rotate(message):
    bot.reply_to(message, f"```text\n{run_command('bash /home/lockboxpi/LCD-show/rotate.sh 90')}\n```", parse_mode="Markdown")


@bot.message_handler(commands=['touch_calib'])
@secure
def handle_touch_calib(message):
    bot.reply_to(message, "Launching Calibration UI...")
    bot.reply_to(message, f"```text\n{run_command('DISPLAY=:0 xinput_calibrator')}\n```", parse_mode="Markdown")


@bot.message_handler(commands=['re_bridge'])
@secure
def handle_re_bridge(message):
    cmd = 'pkill -f bridge.py; nohup python3 /home/lockboxpi/bridge.py > /dev/null 2>&1 & echo "Bridge Restarted"'
    bot.reply_to(message, f"```text\n{run_command(cmd)}\n```", parse_mode="Markdown")


@bot.message_handler(commands=['reboot'])
@secure
def handle_reboot(message):
    bot.reply_to(message, f"```text\n{run_command('sudo reboot')}\n```", parse_mode="Markdown")


# Terminal
@bot.message_handler(commands=['terminal'])
@secure
def handle_terminal(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        cmd = parts[1]
        bot.reply_to(message, f"Executing: `{cmd}`...", parse_mode="Markdown")
        bot.reply_to(message, f"```text\n{run_command(cmd)}\n```", parse_mode="Markdown")
    else:
        bot.reply_to(message, "Usage: /terminal <command>")


# Install APK
@bot.message_handler(commands=['install_apk'])
@secure
def handle_install_apk(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        apk_path = parts[1]
        bot.reply_to(message, f"Installing {apk_path}...")
        bot.reply_to(message, f"```text\n{run_command(f'adb install \"{apk_path}\"')}\n```", parse_mode="Markdown")
    else:
        bot.reply_to(message, "Usage: /install_apk <path_to_apk>")


if __name__ == '__main__':
    print("Bot is starting... Press Ctrl+C to stop.")
    bot.polling(none_stop=True)
