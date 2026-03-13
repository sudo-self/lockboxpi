#!/bin/bash
echo "Installing Bluetooth OBEX Push daemon..."

# Fix SDP Session setup failed by enabling compatibility mode
echo "053053lb" | sudo -S sed -i 's/bluetoothd$/bluetoothd -C/' /lib/systemd/system/bluetooth.service
echo "053053lb" | sudo -S systemctl daemon-reload
echo "053053lb" | sudo -S systemctl restart bluetooth

echo "053053lb" | sudo -S apt-get update
echo "053053lb" | sudo -S apt-get install -y bluez bluez-obexd obexpushd

# Make Bluetooth discoverable and accept files automatically
cat << 'SERVICE' | sudo tee /etc/systemd/system/obexpushd.service
[Unit]
Description=OBEX Push Daemon (Bluetooth File Receiver)
After=bluetooth.service
Requires=bluetooth.service

[Service]
Type=simple
ExecStart=/usr/bin/obexpushd -B23 -n -o /var/www/dumps
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

echo "053053lb" | sudo -S systemctl daemon-reload
echo "053053lb" | sudo -S systemctl enable obexpushd.service
echo "053053lb" | sudo -S systemctl start obexpushd.service

# Configure Bluetooth to be discoverable and named LockboxPi
echo "053053lb" | sudo -S bluetoothctl system-alias "LockboxPi"
echo "053053lb" | sudo -S bluetoothctl discoverable on
echo "053053lb" | sudo -S bluetoothctl pairable on

echo "Bluetooth OBEX Push receiver configured. Files will land in /var/www/dumps"
