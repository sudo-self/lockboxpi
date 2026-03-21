def send_chunks(text):
    for i in range(0, len(text), 4000):
        print(f"```text\n{text[i:i+4000]}\n```")

text = """Output:
 _            _   
| |_ ___  ___| |_ 
| __/ _ \/ __| __|
| ||  __/\__ \ |_ 
 \__\___||___/\__|
"""
send_chunks(text)
