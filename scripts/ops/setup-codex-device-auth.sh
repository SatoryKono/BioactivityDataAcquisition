#!/usr/bin/env bash
# Setup Codex login using device authentication flow
# This script helps configure Codex login via --device-auth
# It checks network connectivity, VPN status, and provides guidance
# for troubleshooting connection issues with auth.openai.com

set -euo pipefail

echo "=== Codex Device Authentication Setup ==="
echo ""

# Check if Codex is installed - prefer direct npm installation
CODEX_DIRECT="/c/Users/Fedor/AppData/Roaming/npm/codex"
CODEX_CMD="codex"

if [[ -x "$CODEX_DIRECT" ]]; then
    CODEX_CMD="$CODEX_DIRECT"
    echo "[OK] Using direct npm Codex at: $CODEX_DIRECT"
elif command -v codex &> /dev/null; then
    echo "[OK] Codex CLI found at: $(command -v codex)"
else
    echo "[ERROR] Codex CLI not found in PATH"
    echo "Install it with: npm install -g @openai/codex"
    exit 1
fi
echo ""

# Check current login status
echo "Checking current login status..."
if $CODEX_CMD login status &> /dev/null; then
    current_status=$($CODEX_CMD login status)
    echo "[INFO] Already logged in: $current_status"
    read -p "Do you want to logout and re-authenticate with device flow? (y/N): " response
    if [[ "$response" != "y" && "$response" != "Y" ]]; then
        echo "Keeping current authentication."
        exit 0
    fi
    $CODEX_CMD logout
    echo "[OK] Logged out successfully"
    echo ""
fi

# Check VPN status (Windows-side VPN detection from WSL)
echo "Checking VPN status..."
if grep -q "NordLynx\|NordVPN\|OpenVPN\|Cisco" /proc/net/route 2>/dev/null; then
    echo "[WARNING] VPN may be active on Windows host"
    echo "[INFO] VPN may block connection to auth.openai.com"
    echo "[INFO] Consider temporarily disabling VPN or adding OpenAI domains to split tunneling"
    echo ""
    read -p "Do you want to continue anyway? (y/N): " vpn_response
    if [[ "$vpn_response" != "y" && "$vpn_response" != "Y" ]]; then
        echo "Please disable VPN and run this script again."
        exit 1
    fi
else
    echo "[OK] No obvious VPN indicators detected"
    echo ""
fi

# Test connectivity to auth.openai.com
echo "Testing connectivity to auth.openai.com..."
if command -v nc &> /dev/null; then
    if nc -z -w5 auth.openai.com 443 2>/dev/null; then
        echo "[OK] Can connect to auth.openai.com:443"
    else
        echo "[WARNING] Cannot connect to auth.openai.com:443"
        echo "[INFO] This may be due to firewall, proxy, or VPN"
        read -p "Continue anyway? (y/N): " continue_response
        if [[ "$continue_response" != "y" && "$continue_response" != "Y" ]]; then
            exit 1
        fi
    fi
elif command -v curl &> /dev/null; then
    if curl -s --connect-timeout 5 https://auth.openai.com > /dev/null 2>&1; then
        echo "[OK] Can connect to auth.openai.com"
    else
        echo "[WARNING] Cannot connect to auth.openai.com"
        echo "[INFO] This may be due to firewall, proxy, or VPN"
        read -p "Continue anyway? (y/N): " continue_response
        if [[ "$continue_response" != "y" && "$continue_response" != "Y" ]]; then
            exit 1
        fi
    fi
else
    echo "[WARNING] Cannot test connectivity (nc/curl not available)"
    echo "[INFO] Continuing with authentication attempt..."
fi
echo ""

# Attempt device authentication
echo "Attempting device authentication..."
echo "[INFO] This will provide a device code for browser verification"
echo ""

if $CODEX_CMD login --device-auth; then
    echo ""
    echo "[SUCCESS] Device authentication completed successfully!"
    echo ""
    
    # Verify login
    verify_check=$($CODEX_CMD login status)
    echo "[INFO] Current login status: $verify_check"
    echo ""
    
    echo "[INFO] Device authentication setup complete!"
    exit 0
else
    echo ""
    echo "[ERROR] Device authentication failed"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Temporarily disable VPN/firewall on Windows host"
    echo "2. Check network connectivity: nc -zv auth.openai.com 443"
    echo "3. Try alternative method: echo \$OPENAI_API_KEY | $CODEX_CMD login --with-api-key"
    echo "4. Check Codex doctor: $CODEX_CMD doctor"
    exit 1
fi
