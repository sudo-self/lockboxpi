import re

with open('/home/lockboxpi/telegram_bot.py', 'r') as f:
    content = f.read()

# 1. Add HEADER_TEXT constant
content = content.replace("TIMEOUT = 120", "TIMEOUT = 120\nHEADER_TEXT = \"[lbpi.JesseJesse.com](https://lbpi.jessejesse.com)       @lockboxtrixie_bot\"")

# 2. Update send_welcome
send_welcome_old = """    try:
        with open(photo_path, 'rb') as f:
            bot.send_photo(message.chat.id, f, caption="[lbpi.JesseJesse.com](https://lbpi.jessejesse.com)       @lockboxtrixie_bot", reply_markup=get_main_menu(), parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "[lbpi.JesseJesse.com](https://lbpi.jessejesse.com)       @lockboxtrixie_bot", reply_markup=get_main_menu(), parse_mode="Markdown")"""

send_welcome_new = """    try:
        with open(photo_path, 'rb') as f:
            bot.send_photo(message.chat.id, f, caption=HEADER_TEXT, reply_markup=get_main_menu(), parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, HEADER_TEXT, reply_markup=get_main_menu(), parse_mode="Markdown")"""
content = content.replace(send_welcome_old, send_welcome_new)

# 3. Update 'Back' and 'Close Menu' buttons
content = content.replace('InlineKeyboardButton("Back"', 'InlineKeyboardButton("« Back"')
content = content.replace('InlineKeyboardButton("Close Menu"', 'InlineKeyboardButton("Dismiss Menu"')

# 4. Update the handle_ui_callbacks edit_message_caption blocks
menu_callbacks_old = """        if data == "menu_main":
            bot.edit_message_caption("[lbpi.JesseJesse.com](https://lbpi.jessejesse.com)       @lockboxtrixie_bot", call.message.chat.id, call.message.message_id, reply_markup=get_main_menu(), parse_mode="Markdown")
        elif data == "menu_adb":
            bot.edit_message_caption("**ADB & Device Tools**", call.message.chat.id, call.message.message_id, reply_markup=get_adb_menu(), parse_mode="Markdown")
        elif data == "menu_mtk":
            bot.edit_message_caption("**MTK Tools**", call.message.chat.id, call.message.message_id, reply_markup=get_mtk_menu(), parse_mode="Markdown")
        elif data == "menu_knife":
            bot.edit_message_caption("**LockKnife Tools**", call.message.chat.id, call.message.message_id, reply_markup=get_knife_menu(), parse_mode="Markdown")
        elif data == "menu_system":
            bot.edit_message_caption("**System & Pi Info**", call.message.chat.id, call.message.message_id, reply_markup=get_system_menu(), parse_mode="Markdown")
        elif data == "menu_files":
            bot.edit_message_caption("**Files & Dumps**", call.message.chat.id, call.message.message_id, reply_markup=get_files_menu(), parse_mode="Markdown")
        elif data == "menu_misc":
            bot.edit_message_caption("**Media & Misc**", call.message.chat.id, call.message.message_id, reply_markup=get_misc_menu(), parse_mode="Markdown")"""

menu_callbacks_new = """        if data == "menu_main":
            bot.edit_message_caption(HEADER_TEXT, call.message.chat.id, call.message.message_id, reply_markup=get_main_menu(), parse_mode="Markdown")
        elif data == "menu_adb":
            bot.edit_message_caption(f"{HEADER_TEXT}\\n\\n**ADB & Device Tools**", call.message.chat.id, call.message.message_id, reply_markup=get_adb_menu(), parse_mode="Markdown")
        elif data == "menu_mtk":
            bot.edit_message_caption(f"{HEADER_TEXT}\\n\\n**MTK Tools**", call.message.chat.id, call.message.message_id, reply_markup=get_mtk_menu(), parse_mode="Markdown")
        elif data == "menu_knife":
            bot.edit_message_caption(f"{HEADER_TEXT}\\n\\n**LockKnife Tools**", call.message.chat.id, call.message.message_id, reply_markup=get_knife_menu(), parse_mode="Markdown")
        elif data == "menu_system":
            bot.edit_message_caption(f"{HEADER_TEXT}\\n\\n**System & Pi Info**", call.message.chat.id, call.message.message_id, reply_markup=get_system_menu(), parse_mode="Markdown")
        elif data == "menu_files":
            bot.edit_message_caption(f"{HEADER_TEXT}\\n\\n**Files & Dumps**", call.message.chat.id, call.message.message_id, reply_markup=get_files_menu(), parse_mode="Markdown")
        elif data == "menu_misc":
            bot.edit_message_caption(f"{HEADER_TEXT}\\n\\n**Media & Misc**", call.message.chat.id, call.message.message_id, reply_markup=get_misc_menu(), parse_mode="Markdown")"""
content = content.replace(menu_callbacks_old, menu_callbacks_new)

# 5. Make the prompts sound more professional
prompts_old = """        if cmd_name == "terminal":
            msg = bot.send_message(call.message.chat.id, "Send the shell command to execute:")
            bot.register_next_step_handler(msg, process_terminal_step)
        elif cmd_name == "installapk":
            msg = bot.send_message(call.message.chat.id, "Send the path or URL of the APK:")
            bot.register_next_step_handler(msg, process_installapk_step)
        elif cmd_name == "sendfile":
            msg = bot.send_message(call.message.chat.id, "Send the filename to send from dumps:")
            bot.register_next_step_handler(msg, process_sendfile_step)
        elif cmd_name == "text2image":
            msg = bot.send_message(call.message.chat.id, "Send the prompt for the image:")
            bot.register_next_step_handler(msg, process_text2image_step)
        elif cmd_name == "ringtone":
            msg = bot.send_message(call.message.chat.id, "Send the YouTube/Video URL for the ringtone:")
            bot.register_next_step_handler(msg, process_ringtone_step)
        elif cmd_name == "figlet":
            msg = bot.send_message(call.message.chat.id, "Send the text for ASCII art:")
            bot.register_next_step_handler(msg, process_figlet_step)
        elif cmd_name == "kick":
            msg = bot.send_message(call.message.chat.id, "Send the User ID to kick:")"""

prompts_new = """        if cmd_name == "terminal":
            msg = bot.send_message(call.message.chat.id, "Please enter the shell command to execute:")
            bot.register_next_step_handler(msg, process_terminal_step)
        elif cmd_name == "installapk":
            msg = bot.send_message(call.message.chat.id, "Please provide the path or URL of the APK:")
            bot.register_next_step_handler(msg, process_installapk_step)
        elif cmd_name == "sendfile":
            msg = bot.send_message(call.message.chat.id, "Please enter the exact filename to send from the dumps directory:")
            bot.register_next_step_handler(msg, process_sendfile_step)
        elif cmd_name == "text2image":
            msg = bot.send_message(call.message.chat.id, "Please enter a detailed prompt for the image generation:")
            bot.register_next_step_handler(msg, process_text2image_step)
        elif cmd_name == "ringtone":
            msg = bot.send_message(call.message.chat.id, "Please provide the video URL to process:")
            bot.register_next_step_handler(msg, process_ringtone_step)
        elif cmd_name == "figlet":
            msg = bot.send_message(call.message.chat.id, "Please enter the text to convert to ASCII art:")
            bot.register_next_step_handler(msg, process_figlet_step)
        elif cmd_name == "kick":
            msg = bot.send_message(call.message.chat.id, "Please provide the User ID to kick from the group:")"""
content = content.replace(prompts_old, prompts_new)

# 6. Make command execution message cleaner
content = content.replace('bot.send_message(call.message.chat.id, f"Running: /{cmd_name}...")', 'bot.send_message(call.message.chat.id, f"Executing `/{cmd_name}`...", parse_mode="Markdown")')
content = content.replace('bot.answer_callback_query(call.id, f"Running {cmd_name}...")', 'bot.answer_callback_query(call.id, f"Executing {cmd_name}...")')


with open('/home/lockboxpi/telegram_bot.py', 'w') as f:
    f.write(content)

