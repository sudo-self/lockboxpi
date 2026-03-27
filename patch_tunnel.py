import re

with open("bridge.py", "r") as f:
    content = f.read()

toggle_endpoint = """
@app.route('/tunnel/toggle', methods=['POST'])
def toggle_tunnel():
    current = get_tunnel_url()
    try:
        if current:
            subprocess.run(["sudo", "tailscale", "funnel", "off"])
            return jsonify(status="TUNNEL OFF")
        else:
            subprocess.run(["sudo", "tailscale", "funnel", "--bg", "8080"])
            return jsonify(status="TUNNEL ON")
    except Exception as e:
        return jsonify(status=f"ERROR: {str(e)}")
"""

if "/tunnel/toggle" not in content:
    content = content.replace("# --- 5.5 UDID ENROLLMENT RECEIVER ---", toggle_endpoint + "\n# --- 5.5 UDID ENROLLMENT RECEIVER ---")
    with open("bridge.py", "w") as f:
        f.write(content)
