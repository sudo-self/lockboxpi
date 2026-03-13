#!/bin/bash

DOMAIN="lbpi.jessejesse.com"
TUNNEL_NAME="lockboxpi"

echo "Setting up persistent Cloudflare tunnel for $DOMAIN..."

# Create cloudflared directory and save the cert.pem token
mkdir -p /root/.cloudflared
cp /home/lockboxpi/cert.pem /root/.cloudflared/cert.pem
chmod 600 /root/.cloudflared/cert.pem

# Cleanup any existing quick tunnel services
systemctl stop lockbox-tunnel.service 2>/dev/null
systemctl disable lockbox-tunnel.service 2>/dev/null
rm -f /etc/systemd/system/lockbox-tunnel.service

# Force delete if exists to regenerate the credentials json
cloudflared tunnel delete -f $TUNNEL_NAME 2>/dev/null || true
cloudflared tunnel create $TUNNEL_NAME

# Extract the UUID of the tunnel
TUNNEL_UUID=$(cloudflared tunnel list | grep -w $TUNNEL_NAME | awk '{print $1}')

if [ -z "$TUNNEL_UUID" ]; then
    echo "ERROR: Failed to create or find tunnel $TUNNEL_NAME."
    exit 1
fi

echo "Tunnel UUID: $TUNNEL_UUID"

# Route the DNS to your domain
cloudflared tunnel route dns -f $TUNNEL_UUID $DOMAIN || true

# Create the persistent config file
mkdir -p /etc/cloudflared
cat << YML > /etc/cloudflared/config.yml
tunnel: $TUNNEL_UUID
credentials-file: /root/.cloudflared/$TUNNEL_UUID.json

ingress:
  - hostname: $DOMAIN
    service: http://localhost:80
  - service: http_status:404
YML

# Install and start the official cloudflared service
cloudflared service install 2>/dev/null || true
systemctl daemon-reload
systemctl enable cloudflared
systemctl restart cloudflared

echo "Persistent Tunnel service installed!"
echo "Your Tectonic Utility is now permanently mapped to: https://$DOMAIN"
