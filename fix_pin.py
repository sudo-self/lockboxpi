with open("telegram_bot.py", "r") as f:
    content = f.read()

content = content.replace("secret = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')", "secret = TOKEN")

with open("telegram_bot.py", "w") as f:
    f.write(content)
print("Fixed TOKEN")
