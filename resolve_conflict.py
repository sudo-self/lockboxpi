import sys

with open('telegram_bot.py', 'r') as f:
    lines = f.readlines()

resolved_lines = []
in_conflict = False
conflict_section = []
conflict_state = None # None, 'HEAD', 'MERGE'

for line in lines:
    if line.startswith('<<<<<<< HEAD'):
        in_conflict = True
        conflict_state = 'HEAD'
        continue
    elif line.startswith('======='):
        conflict_state = 'MERGE'
        continue
    elif line.startswith('>>>>>>>'):
        # We want to keep the MERGE side (my changes) and discard HEAD
        in_conflict = False
        conflict_state = None
        continue
    
    if not in_conflict:
        resolved_lines.append(line)
    elif conflict_state == 'MERGE':
        resolved_lines.append(line)
        
with open('telegram_bot.py', 'w') as f:
    f.writelines(resolved_lines)

print("Conflict resolved.")
