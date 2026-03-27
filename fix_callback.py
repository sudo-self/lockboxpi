with open("telegram_bot.py", "r") as f:
    content = f.read()

content = content.replace('elif cmd_name == "samsung": handle_samsung(call.message)\n        elif cmd_name == "diagnostic": handle_diagnostic(call.message)', 'elif cmd_name == "samsung": handle_samsung(call.message)')
content = content.replace('elif cmd_name == "samsung": handle_samsung(call.message)', 'elif cmd_name == "samsung": handle_samsung(call.message)\n        elif cmd_name == "diagnostic": handle_diagnostic(call.message)')

with open("telegram_bot.py", "w") as f:
    f.write(content)
print("Fixed callback")
