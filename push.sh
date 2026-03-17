#!/bin/bash
PI_IP="lockboxpi.local"
PI_USER="lockboxpi"
KEY="my_private_key"

# Enable SSH Multiplexing to reuse the same connection
SSH_OPTS="-6 -i $KEY -o ControlMaster=auto -o ControlPath=/tmp/ssh-%r@%h:%p -o ControlPersist=10m -o StrictHostKeyChecking=accept-new"
RSYNC_CMD="rsync -avz -e \"ssh $SSH_OPTS\""

echo "Deploying to LockboxPi ($PI_IP)..."

# 1. Push Core Files
eval "$RSYNC_CMD index.html $PI_USER@$PI_IP:/var/www/index.html"
eval "$RSYNC_CMD bridge.py $PI_USER@$PI_IP:/var/www/bridge.py"
if [ -f "report_boot.py" ]; then
    eval "$RSYNC_CMD report_boot.py $PI_USER@$PI_IP:/var/www/report_boot.py"
fi

# 2. Push Dumps Folder
if [ -d "dumps" ]; then
    echo "Syncing dumps repository..."
    eval "$RSYNC_CMD dumps/ $PI_USER@$PI_IP:/var/www/dumps/"
    eval "$RSYNC_CMD dumps/icons/ $PI_USER@$PI_IP:/var/www/"
fi

# 3. Handle Header
if [ -f "header.html" ]; then
    eval "$RSYNC_CMD header.html $PI_USER@$PI_IP:/var/www/dumps/header.html"
fi

# 4. Handle Apache Config and Cloudflare Tunnel
if [ -f "dumps.conf" ]; then
    eval "$RSYNC_CMD dumps.conf $PI_USER@$PI_IP:/home/lockboxpi/dumps.conf"
fi
if [ -f "setup_tunnel.sh" ]; then
    eval "$RSYNC_CMD cert.pem fix_touch.sh $PI_USER@$PI_IP:/home/lockboxpi/"
    eval "$RSYNC_CMD setup_tunnel.sh $PI_USER@$PI_IP:/home/lockboxpi/setup_tunnel.sh"
fi
if [ -f "setup_ssl.sh" ]; then
    eval "$RSYNC_CMD setup_ssl.sh $PI_USER@$PI_IP:/home/lockboxpi/setup_ssl.sh"
fi

# 5. Remote Commands with X11 Authority fix
ssh $SSH_OPTS lockboxpi@$PI_IP "
    echo '053053lb' | sudo -S mv /home/lockboxpi/dumps.conf /etc/apache2/conf-enabled/dumps.conf && \
    echo '053053lb' | sudo -S bash /home/lockboxpi/setup_tunnel.sh && \
    echo '053053lb' | sudo -S bash /home/lockboxpi/setup_ssl.sh && \
    echo '053053lb' | sudo -S chown -R lockboxpi:www-data /var/www && \
    echo '053053lb' | sudo -S chmod -R 755 /var/www && \
    echo '053053lb' | sudo -S chmod -R 777 /var/www/dumps && \
    # Remove Bluetooth completely
    echo '053053lb' | sudo -S systemctl stop bluetooth 2>/dev/null || true && \
    echo '053053lb' | sudo -S systemctl disable bluetooth 2>/dev/null || true && \
    echo '053053lb' | sudo -S rfkill block bluetooth 2>/dev/null || true && \
    # Touch screen fixes
    echo 'xinput set-prop \"ADS7846 Touchscreen\" \"Coordinate Transformation Matrix\" -1 0 1 0 1 0 0 0 1 || true' >> /home/lockboxpi/.xsessionrc && \
    echo 'xinput set-prop \"ADS7846 Touchscreen\" \"Evdev Axis Inversion\" 1 0 || true' >> /home/lockboxpi/.xsessionrc && \
    chmod +x /home/lockboxpi/.xsessionrc && \
    echo '053053lb' | sudo -S systemctl restart lockbox-bridge.service && \
    echo '053053lb' | sudo -S systemctl reload apache2 && \
    export DISPLAY=:0 && \
    export XAUTHORITY=/home/lockboxpi/.Xauthority && \
    xdotool key ctrl+F5
"

echo "Deployment complete! Screen hard-refreshed."

# 6. Git commit and push local repo
echo "Committing and pushing local changes to git..."
git add .
git commit -m "Auto-deploy update via push.sh"
git push