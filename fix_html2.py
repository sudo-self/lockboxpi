with open('/home/lockboxpi/telegram_bot.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'parse_mode="HTML"' in line and 'send_message' in line and 'send_chunks' in line:
         # send_chunks issue
         line = line.replace('```text', '<pre>')
         line = line.replace('```', '</pre>')
    elif 'parse_mode="HTML"' in line and 'listdumps' in line:
         line = line.replace('```', '<pre>')
         line = line.replace('```', '</pre>')
    new_lines.append(line)

content = "".join(new_lines)
# Just hardcode the chunks replacement.
content = content.replace('f"<pre>\\n{text[i:i+4000]}\\n</pre>"', 'f"<pre>{text[i:i+4000]}</pre>"')

with open('/home/lockboxpi/telegram_bot.py', 'w') as f:
    f.write(content)
