import re
with open("telegram_bot.py", "r") as f:
    content = f.read()

pin_code = """
import time
import hmac
import hashlib

def generate_pin(offset_minutes=0):
    secret = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
    if not secret: return None
    window_ms = 15 * 60 * 1000
    time_window = int((time.time() * 1000 + (offset_minutes * 60 * 1000)) // window_ms)
    
    hash_obj = hmac.new(secret.encode('utf-8'), str(time_window).encode('utf-8'), hashlib.sha256).hexdigest()
    pin = int(hash_obj[:8], 16) % 1000000
    return str(pin).zfill(6)

@bot.message_handler(commands=['diagnostic'])
@secure
def handle_diagnostic(message):
    markup = InlineKeyboardMarkup()
    pin = generate_pin(0)
    markup.add(InlineKeyboardButton(f"PIN: {pin}", callback_data="diag_noop"), InlineKeyboardButton("Cancel", callback_data="diag_cancel"))
    bot.reply_to(message, "Diagnostic Link: https://device-id-bot.vercel.app/\n\n_This PIN is valid for the next 15 minutes._", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('diag_'))
def handle_diagnostic_callbacks(call):
    if call.from_user.id not in ALLOWED_USERS: bot.answer_callback_query(call.id, "Unauthorized"); return
    if call.data == "diag_cancel": 
        bot.answer_callback_query(call.id)
        bot.edit_message_text("Canceled.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "Use this PIN on the website.")
"""

# Find where to insert
samsung_idx = content.find("def handle_samsung(message):")
insert_idx = content.rfind("@bot.message_handler", 0, samsung_idx)

new_content = content[:insert_idx] + pin_code + "\n" + content[insert_idx:]

# Also patch COMMAND_DESCRIPTIONS
new_content = new_content.replace('"dropzone":"dropzone.png",', '"diagnostic": "Diagnostic tool", "dropzone":"dropzone.png",')

with open("telegram_bot.py", "w") as f:
    f.write(new_content)

print("Patched.")
