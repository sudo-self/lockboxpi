with open('telegram_bot.py', 'r') as f:
    text = f.read()

bad_block = """        body = (
            "<b>Active lockboxPRO Endpoints</b>\\n\\n"
            + public
            + f"\\n\\n<b>Local Network:</b>\\n"
• <code>http://{local_ip}:8080</code>"
        )"""

good_block = """        body = (
            "<b>Active lockboxPRO Endpoints</b>\\n\\n"
            + public
            + f"\\n\\n<b>Local Network:</b>\\n• <code>http://{local_ip}:8080</code>"
        )"""

text = text.replace(bad_block, good_block)

with open('telegram_bot.py', 'w') as f:
    f.write(text)
