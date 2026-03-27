import os
os.environ['ALLOWED_USERS'] = '7251722622'
ALLOWED_USERS_RAW = os.getenv('ALLOWED_USERS', '0')
ALLOWED_USERS = [int(u.strip()) for u in ALLOWED_USERS_RAW.split(',') if u.strip().replace('-', '').isdigit()]
print("ALLOWED_USERS:", ALLOWED_USERS)
print(7251722622 in ALLOWED_USERS)
