with open('/home/lockboxpi/telegram_bot.py', 'r') as f:
    content = f.read()

content = content.replace('```text', '<pre>')
content = content.replace('```', '</pre>')
content = content.replace('`/{cmd_name}`', '<code>/{cmd_name}</code>')

with open('/home/lockboxpi/telegram_bot.py', 'w') as f:
    f.write(content)
