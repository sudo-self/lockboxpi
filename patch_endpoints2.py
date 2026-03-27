import re

with open("telegram_bot.py", "r") as f:
    content = f.read()

new_handle_endpoints = """def handle_endpoints(message):
    try:
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
        except: pass
                
        # 2. Cloudflare
        try:
            cf_res = subprocess.run(["systemctl", "is-active", "cloudflared"], capture_output=True, text=True)
            if cf_res.stdout.strip() == "active":
                funnel_urls.append("• <b>Cloudflare:</b> <code>https://lbpi.jessejesse.com</code>")
        except: pass

        try:
            local_ip = subprocess.check_output(["hostname", "-I"]).decode().split()[0]
        except Exception:
            local_ip = "127.0.0.1"

        public = (
            "<b>Public Endpoints:</b>\\n" + "\\n".join(funnel_urls)
            if funnel_urls
            else "<b>Public:</b> No active funnels detected."
        )
        body = (
            "<b>Active lockboxPRO Endpoints</b>\\n\\n"
            + public
            + f"\\n\\n<b>Local Network:</b>\\n• <code>http://{local_ip}:8080</code>"
        )
        bot.send_message(message.chat.id, body, parse_mode="HTML", disable_web_page_preview=True)

    except Exception as exc:
        bot.reply_to(message, f"Exception: {exc}")"""

content = re.sub(
    r"def handle_endpoints\(message\):.*?except Exception as exc:\n\s+bot\.reply_to\(message, f\"Exception: \{exc\}\"\)",
    new_handle_endpoints,
    content,
    flags=re.DOTALL
)

with open("telegram_bot.py", "w") as f:
    f.write(content)
