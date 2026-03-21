import re

with open('/home/lockboxpi/telegram_bot.py', 'r') as f:
    content = f.read()

# Replace send_welcome
send_welcome_replacement = """@bot.message_handler(commands=['start', 'help', 'commands', 'menu'])
def send_welcome(message):
    photo_path = os.path.join(DUMPS_DIR, "pi.jpg")
    try:
        with open(photo_path, 'rb') as f:
            bot.send_photo(message.chat.id, f, caption="**Main Menu**\\nSelect a category below or send a file to upload:", reply_markup=get_main_menu(), parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"**Main Menu**\\nSelect a category below or send a file to upload:\\n{e}", reply_markup=get_main_menu(), parse_mode="Markdown")
"""
content = re.sub(r"@bot.message_handler\(commands=\['start', 'help', 'commands', 'menu'\]\)\ndef send_welcome\(message\):\n    bot.reply_to\(message, \".*?\", reply_markup=get_main_menu\(\), parse_mode=\"Markdown\"\)\n", send_welcome_replacement, content)

# Replace bot.edit_message_text for menu callbacks
menu_callbacks = [
    "**Main Menu**\\nSelect a category:",
    "**ADB & Device Tools**",
    "**MTK Tools**",
    "**LockKnife Tools**",
    "**System & Pi Info**",
    "**Files & Dumps**",
    "**Media & Misc**"
]

for menu_text in menu_callbacks:
    # Need to match lines like: bot.edit_message_text("**Main Menu**\nSelect a category:", call.message.chat.id, call.message.message_id, reply_markup=get_main_menu(), parse_mode="Markdown")
    # Because of newlines in string, regex might be tricky. Let's just do a blanket replace for the block.
    pass

# We can replace all bot.edit_message_text in the "menu_" branch.
# Let's find the menu_ block:
menu_block_pattern = r"(if data\.startswith\(\"menu_\"\):\n.*?bot\.answer_callback_query.*?)\n(.*?)return"
match = re.search(menu_block_pattern, content, flags=re.DOTALL)
if match:
    old_block = match.group(2)
    new_block = old_block.replace("bot.edit_message_text", "bot.edit_message_caption")
    content = content.replace(old_block, new_block)

with open('/home/lockboxpi/telegram_bot.py', 'w') as f:
    f.write(content)
