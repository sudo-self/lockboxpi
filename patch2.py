import re

with open('/home/lockboxpi/telegram_bot.py', 'r') as f:
    content = f.read()

# Replace send_welcome block
pattern = r"@bot\.message_handler\(commands=\['start', 'help', 'commands', 'menu'\]\)\ndef send_welcome\(message\):.*?def handle_endpoints\(message\):"
replacement = """@bot.message_handler(commands=['start', 'help', 'commands', 'menu'])
def send_welcome(message):
    photo_path = os.path.join(DUMPS_DIR, "photo_AgACAgEAAyEFAATc-fVDAAIBiWm72nPdVFfe0GhSP8od2_LSJVkTAAK_C2sbH-fhRTl5vr5l8M2iAQADAgADeAADOgQ.jpg")
    try:
        with open(photo_path, 'rb') as f:
            bot.send_photo(message.chat.id, f, caption="[lbpi.JesseJesse.com](https://lbpi.jessejesse.com)", reply_markup=get_main_menu(), parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "[lbpi.JesseJesse.com](https://lbpi.jessejesse.com)", reply_markup=get_main_menu(), parse_mode="Markdown")

@bot.message_handler(commands=['endpoints'])
@secure
def handle_endpoints(message):"""

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Replace the specific text inside the callback
content = content.replace('bot.edit_message_caption("**Main Menu**\\nSelect a category:",', 'bot.edit_message_caption("[lbpi.JesseJesse.com](https://lbpi.jessejesse.com)",')

with open('/home/lockboxpi/telegram_bot.py', 'w') as f:
    f.write(content)
