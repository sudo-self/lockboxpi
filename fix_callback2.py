with open("telegram_bot.py", "r") as f:
    content = f.read()

import re
content = re.sub(r'(elif cmd_name == "diagnostic": handle_diagnostic\(call.message\)\s*)+', 'elif cmd_name == "diagnostic": handle_diagnostic(call.message)\n        ', content)

# ensure label is descriptive
content = content.replace('InlineKeyboardButton("Diagnostic Tool"', 'InlineKeyboardButton("Device ID Endpoint"')

with open("telegram_bot.py", "w") as f:
    f.write(content)
print("Cleaned up")
