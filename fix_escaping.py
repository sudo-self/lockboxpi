import re

with open('/home/lockboxpi/telegram_bot.py', 'r') as f:
    content = f.read()

# Telegram's standard Markdown parser is very tricky with underscores.
# It's safer to just switch to MarkdownV2 and escape the necessary characters,
# but to keep it simple and fix it immediately, we will use an HTML zero-width space
# or just remove the markdown parsing for that specific text, OR use backticks to make it code.
# Let's just escape it properly for Markdown by using an inline code block for the username,
# or escaping the underscore by using MarkdownV2 parsing, but changing parse_mode would break the rest.
# Easiest fix for Markdown (v1) is to just avoid the raw underscore if it's not enclosed.
# Alternatively, wrap the username in backticks ` `@lockboxtrixie_bot` `

old_header = 'HEADER_TEXT = "[lbpi.JesseJesse.com](https://lbpi.jessejesse.com)       @lockboxtrixie\\\\_bot"'
new_header = 'HEADER_TEXT = "[lbpi.JesseJesse.com](https://lbpi.jessejesse.com)       @lockboxtrixie_bot"'

content = content.replace(old_header, new_header)

# Actually, if we just remove the `parse_mode="Markdown"` when sending the username, we lose the link.
# Let's just wrap the username in code block ` `@lockboxtrixie_bot` ` so Markdown ignores the underscore.
content = content.replace('HEADER_TEXT = "[lbpi.JesseJesse.com](https://lbpi.jessejesse.com)       @lockboxtrixie_bot"', 'HEADER_TEXT = "[lbpi.JesseJesse.com](https://lbpi.jessejesse.com)       `@lockboxtrixie_bot`"')


with open('/home/lockboxpi/telegram_bot.py', 'w') as f:
    f.write(content)
