#!/bin/bash

# Create cloudflared directory and save the cert.pem token
mkdir -p /home/lockboxpi/.cloudflared
cp /home/lockboxpi/cert.pem /home/lockboxpi/.cloudflared/cert.pem
chown -R lockboxpi:lockboxpi /home/lockboxpi/.cloudflared
chmod 600 /home/lockboxpi/.cloudflared/cert.pem

# Create the systemd service for the Quick Tunnel
cat << 'EOF' > /etc/systemd/system/lockbox-tunnel.service
[Unit]
Description=LockboxPi Cloudflare Quick Tunnel
After=network-online.target

[Service]
Type=simple
User=root
ExecStart=/bin/bash -c '/usr/bin/cloudflared tunnel --url http://localhost:80 2>&1 | tee /tmp/cloudflared.log'
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Reload and enable the service
systemctl daemon-reload
systemctl enable lockbox-tunnel.service
systemctl restart lockbox-tunnel.service

echo "Tunnel service installed and started."
