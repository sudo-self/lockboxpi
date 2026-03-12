#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
echo "053053lb" | sudo -S apt-get update
echo "053053lb" | sudo -S apt-get install -y docker.io docker-compose git nodejs npm
echo "053053lb" | sudo -S systemctl enable docker
echo "053053lb" | sudo -S systemctl start docker

cd /home/lockboxpi
if [ ! -d "snapdrop" ]; then
    git clone https://github.com/RobinLinus/snapdrop.git
fi
cd snapdrop
echo "053053lb" | sudo -S docker-compose up -d
