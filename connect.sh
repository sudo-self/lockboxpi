#!/bin/bash
PI_IP="lockboxpi.local"
PI_USER="lockboxpi"
KEY="my_private_key"

echo "Connecting to LockboxPi ($PI_IP)..."
ssh -6 -i $KEY -o StrictHostKeyChecking=accept-new $PI_USER@$PI_IP "$@"
