import subprocess
import json

funnel_urls = []

# 1. Tailscale
try:
    res = subprocess.run(
        ["tailscale", "serve", "status", "--json"],
        capture_output=True, text=True, timeout=5,
    )
    if res.returncode == 0 and res.stdout.strip():
        data = json.loads(res.stdout)
        for host, cfg in data.get("Web", {}).items():
            host_clean = host[:-4] if host.endswith(":443") else host
            for path in cfg.get("Handlers", {}).keys():
                path_clean = path if path != "/" else ""
                url = f"https://{host_clean}{path_clean}"
                funnel_urls.append(f"• <b>Tailscale:</b> <code>{url}</code>")

        if data.get("TCP"):
            st = subprocess.run(
                ["tailscale", "status", "--json"], capture_output=True, text=True
            )
            node = json.loads(st.stdout).get("Self", {}).get("DNSName", "lockboxpi").rstrip(".")
            for port in data["TCP"].keys():
                funnel_urls.append(f"• <b>Tailscale TCP:</b> <code>{node}:{port}</code>")
except Exception as e:
    pass

# 2. Cloudflare
try:
    cf_res = subprocess.run(["systemctl", "is-active", "cloudflared"], capture_output=True, text=True)
    if cf_res.stdout.strip() == "active":
        funnel_urls.append("• <b>Cloudflare:</b> <code>https://lbpi.jessejesse.com</code>")
except Exception as e:
    pass

try:
    local_ip = subprocess.check_output(["hostname", "-I"]).decode().split()[0]
except Exception:
    local_ip = "127.0.0.1"
    
try:
    hostname = subprocess.check_output(["hostname"]).decode().strip()
    mdns = f"{hostname}.local"
except:
    mdns = "lockboxpi.local"

public = (
    "<b>Public Endpoints:</b>\n" + "\n".join(funnel_urls)
    if funnel_urls
    else "<b>Public:</b> No active funnels detected."
)
body = (
    "<b>Active lockboxPRO Endpoints</b>\n\n"
    + public
    + f"\n\n<b>Local Network (UI):</b>\n"
    + f"• <code>http://{mdns}:8080</code>\n"
    + f"• <code>http://{local_ip}:8080</code>\n\n"
    + f"<b>Local Network (Vault):</b>\n"
    + f"• <code>http://{mdns}:8084</code>\n"
    + f"• <code>http://{local_ip}:8084</code>"
)
print(body)
