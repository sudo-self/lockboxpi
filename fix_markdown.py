import re

with open('/home/lockboxpi/telegram_bot.py', 'r') as f:
    content = f.read()

# The underscore in @lockboxtrixie_bot is causing the Markdown parser to expect a matching underscore for italics
# We escape it: @lockboxtrixie\_bot
content = content.replace("@lockboxtrixie_bot", "@lockboxtrixie\\_bot")

with open('/home/lockboxpi/telegram_bot.py', 'w') as f:
    f.write(content)
