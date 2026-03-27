import re

with open('/home/lockboxpi/telegram_bot.py', 'r') as f:
    code = f.read()

new_is_allowed = '''def is_allowed(message) -> bool:
    uid = message.from_user.id
    cid = message.chat.id
    
    logging.info(f"Checking access: user={uid}, chat={cid}")
    
    if cid in ALLOWED_GROUPS:
        return True
    
    user_ok = not ALLOWED_USERS or uid in ALLOWED_USERS
    chat_ok = CHAT_ID == 0 or cid == CHAT_ID
    return user_ok and chat_ok'''

code = re.sub(r'def is_allowed\(message\) -> bool:[\s\S]*?return user_ok and chat_ok', new_is_allowed, code)

with open('/home/lockboxpi/telegram_bot.py', 'w') as f:
    f.write(code)
