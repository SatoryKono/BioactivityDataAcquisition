#!/bin/bash
set -e

echo "Starting Cloudflare WARP..."

# Register the device if needed
if [ ! -f /var/run/warp/token ]; then
    echo "Registering device with WARP..."
    warp-cli registration new
fi

# Connect to WARP
echo "Connecting to WARP..."
warp-cli connect

# Enable 1.1.1.1 for Families or standard DNS
warp-cli set-mode proxy

# Check connection status
echo "WARP Status:"
warp-cli status

# Keep container running
echo "Container is ready. WARP is active."
tail -f /dev/null
