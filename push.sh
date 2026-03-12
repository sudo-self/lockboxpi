#!/bin/bash
PI_IP="lockboxpi.local"
PI_USER="lockboxpi"

echo "Deploying to LockboxPi ($PI_IP)..."

# 1. Push Core Files
scp index.html $PI_USER@$PI_IP:/var/www/index.html
scp bridge.py $PI_USER@$PI_IP:/var/www/bridge.py
if [ -f "report_boot.py" ]; then
    scp report_boot.py $PI_USER@$PI_IP:/var/www/report_boot.py
fi

# 2. Push Dumps Folder
if [ -d "dumps" ]; then
    echo "Syncing dumps repository..."
    scp -r dumps/* $PI_USER@$PI_IP:/var/www/dumps/
fi

# 3. Handle Header
if [ -f "header.html" ]; then
    scp header.html $PI_USER@$PI_IP:/var/www/dumps/header.html
fi

# 4. Handle Apache Config and Cloudflare Tunnel
if [ -f "dumps.conf" ]; then
    scp dumps.conf $PI_USER@$PI_IP:/home/lockboxpi/dumps.conf
fi
if [ -f "setup_tunnel.sh" ]; then
    scp cert.pem $PI_USER@$PI_IP:/home/lockboxpi/cert.pem
    scp setup_tunnel.sh $PI_USER@$PI_IP:/home/lockboxpi/setup_tunnel.sh
fi

# 5. Remote Commands with X11 Authority fix
# We point to the lockboxpi user's .Xauthority file to gain control of the screen
ssh lockboxpi@$PI_IP "
    echo '053053lb' | sudo -S mv /home/lockboxpi/dumps.conf /etc/apache2/conf-enabled/dumps.conf && \
    echo '053053lb' | sudo -S bash /home/lockboxpi/setup_tunnel.sh && \
    echo '053053lb' | sudo -S chown -R lockboxpi:www-data /var/www && \
    echo '053053lb' | sudo -S chmod -R 755 /var/www && \
    echo '053053lb' | sudo -S chmod -R 777 /var/www/dumps && \
    echo '053053lb' | sudo -S systemctl restart lockbox-bridge.service && \
    echo '053053lb' | sudo -S systemctl reload apache2 && \
    export DISPLAY=:0 && \
    export XAUTHORITY=/home/lockboxpi/.Xauthority && \
    xdotool key ctrl+F5
"

echo "Deployment complete! Screen hard-refreshed."
