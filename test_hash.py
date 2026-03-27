import time, hmac, hashlib
def generate_pin(secret, offset_minutes=0):
    window_ms = 15 * 60 * 1000
    time_window = int((time.time() * 1000 + (offset_minutes * 60 * 1000)) // window_ms)
    hash_obj = hmac.new(secret.encode('utf-8'), str(time_window).encode('utf-8'), hashlib.sha256).hexdigest()
    pin = int(hash_obj[:8], 16) % 1000000
    return {"pin": str(pin).zfill(6), "timeWindow": time_window, "hash": hash_obj[:8]}
print(generate_pin('8698638609:AAEaE1oKl1307vB11rOK_RoDniiAm2BeELY', 0))
