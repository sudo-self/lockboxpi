with open("telegram_bot.py", "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

# Try to remove the exact sequence of junk.
clean = content.replace("</pre>", "")

with open("telegram_bot_cleaned.py", "w", encoding="utf-8") as f:
    f.write(clean)
