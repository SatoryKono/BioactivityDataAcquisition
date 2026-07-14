#!/bin/bash
# Script to fix DNS in WSL for device-auth

set -e

echo "========================================"
echo "WSL DNS Setup for Codex Device Auth"
echo "========================================"
echo ""

# Check if running in WSL
if ! grep -qi microsoft /proc/version; then
    echo "ERROR: This script must be run in WSL"
    exit 1
fi

# Step 1: Configure wsl.conf to disable automatic resolv.conf generation
echo "Step 1: Configuring /etc/wsl.conf..."
sudo bash -c 'cat > /etc/wsl.conf << EOF
[boot]
systemd=true

[user]
default=fedor

[network]
generateResolvConf = false
EOF'

echo "✓ /etc/wsl.conf configured"
echo ""

# Step 2: Configure static DNS in resolv.conf
echo "Step 2: Configuring /etc/resolv.conf with Google DNS..."
sudo bash -c 'cat > /etc/resolv.conf << EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF'

echo "✓ /etc/resolv.conf configured"
echo ""

# Step 3: Protect resolv.conf from being overwritten
echo "Step 3: Protecting /etc/resolv.conf from overwrites..."
sudo chattr +i /etc/resolv.conf
echo "✓ /etc/resolv.conf is now immutable"
echo ""

# Step 4: Test DNS resolution
echo "Step 4: Testing DNS resolution..."
if ping -c 1 -W 2 auth.openai.com > /dev/null 2>&1; then
    echo "✓ DNS resolution working for auth.openai.com"
else
    echo "⚠ DNS resolution still failing for auth.openai.com"
    echo "  You may need to restart WSL"
fi
echo ""

echo "========================================"
echo "DNS Setup Complete"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Restart WSL from PowerShell: wsl --shutdown"
echo "2. Start WSL again: wsl"
echo "3. Test device-auth: codex login --device-auth"
echo ""
echo "To undo these changes:"
echo "  sudo chattr -i /etc/resolv.conf"
echo "  Remove [network] section from /etc/wsl.conf"
echo "  Restart WSL"