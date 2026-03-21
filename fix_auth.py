import re

with open('/home/lockboxpi/telegram_bot.py', 'r') as f:
    content = f.read()

# Fix the auth check in handle_ui_callbacks
auth_old = """@bot.callback_query_handler(func=lambda call: call.data.startswith(('menu_', 'run_', 'prompt_')))
def handle_ui_callbacks(call):
    user_ok = call.from_user.id in ALLOWED_USERS
    chat_ok = (CHAT_ID == 0) or (call.message.chat.id == CHAT_ID)
    if not (user_ok and chat_ok):
        bot.answer_callback_query(call.id, "Unauthorized")
        return"""

auth_new = """@bot.callback_query_handler(func=lambda call: call.data.startswith(('menu_', 'run_', 'prompt_')))
def handle_ui_callbacks(call):
    user_ok = (len(ALLOWED_USERS) == 0) or (call.from_user.id in ALLOWED_USERS)
    chat_ok = (CHAT_ID == 0) or (call.message.chat.id == CHAT_ID)
    if not (user_ok and chat_ok):
        bot.answer_callback_query(call.id, "Unauthorized")
        return"""

content = content.replace(auth_old, auth_new)

# Also fix the global is_allowed function just in case
is_allowed_old = """def is_allowed(message):
    user_ok = message.from_user.id in ALLOWED_USERS
    chat_ok = (CHAT_ID == 0) or (message.chat.id == CHAT_ID)
    return user_ok and chat_ok"""

is_allowed_new = """def is_allowed(message):
    user_ok = (len(ALLOWED_USERS) == 0) or (message.from_user.id in ALLOWED_USERS)
    chat_ok = (CHAT_ID == 0) or (message.chat.id == CHAT_ID)
    return user_ok and chat_ok"""

content = content.replace(is_allowed_old, is_allowed_new)

with open('/home/lockboxpi/telegram_bot.py', 'w') as f:
    f.write(content)
