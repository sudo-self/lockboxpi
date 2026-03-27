import re
with open('/home/lockboxpi/telegram_bot.py', 'r') as f:
    content = f.read()

commands_block = """COMMAND_DESCRIPTIONS = {
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
    cmd_list = "\\n".join([f"/{k} - {v}" for k, v in sorted(COMMAND_DESCRIPTIONS.items())])
    bot.reply_to(message, f"<b>Available Commands:</b>\\n<pre>{cmd_list}</pre>", parse_mode="HTML")

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
    print("lockboxPRO bot starting…")"""

content = re.sub(
    r"# ─────────────────────────────────────────────\n# Start\n# ─────────────────────────────────────────────\n\nif __name__ == \"__main__\":\n    print\(\"lockboxPRO bot starting…\"\)",
    commands_block,
    content
)

with open('/home/lockboxpi/telegram_bot.py', 'w') as f:
    f.write(content)
