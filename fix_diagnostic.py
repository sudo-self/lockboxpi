with open("telegram_bot.py", "r") as f:
    content = f.read()

bad_str = 'bot.reply_to(message, "Diagnostic Link: https://device-id-bot.vercel.app/\n\n_This PIN is valid for the next 15 minutes._", reply_markup=markup, parse_mode="Markdown")'
good_str = 'bot.reply_to(message, "Diagnostic Link: https://device-id-bot.vercel.app/\\n\\n_This PIN is valid for the next 15 minutes._", reply_markup=markup, parse_mode="Markdown")'

content = content.replace(bad_str, good_str)

with open("telegram_bot.py", "w") as f:
    f.write(content)
print("Fixed syntax")
