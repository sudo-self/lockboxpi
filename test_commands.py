BOT_COMMANDS = {
    "menu": "Show Bot Menu", "adb":"Checks ADB", "adbbootloader":"reboot bl", "adbdevices":"devices", "commands":"Lists commands", "diskfree":"Disk space",
    "dropzone":"dropzone.png", "endpoints":"Pi endpoints", "figlet":"ASCII art", "installapk":"Install APK", "invite":"Invite link",
    "ipaddr":"IP address", "kick":"Kick user", "knifedumpr":"Knife dump", "knifekey":"Knife key", "listdumps":"List dumps",
    "lockboxpi":"Sys info", "lsusb":"USB devices", "mtkefrp":"MTK E-FRP", "mtkfrp":"MTK FRP", "mtkgettargetconfig":"MTK config",
    "mtkgpt":"MTK GPT", "mtkhelp":"MTK help", "mtkunlock":"MTK unlock", "reboot":"Reboot", "rebridge":"Restart bridge",
    "ringtone":"Create ringtone", "samsung":"Samsung FRP", "sendfile":"Send file", "syslog":"System log", "terminal":"Shell command",
    "text2image":"Gen image", "touchcalib":"Calibrate", "touchrotate":"Rotate", "whoami":"User info", "x":"Twitter"
}
for k,v in sorted(BOT_COMMANDS.items()):
    print(f"/{k} - {v}")
