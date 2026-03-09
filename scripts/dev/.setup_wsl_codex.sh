#!/bin/bash
# Fix OpenAI connectivity in WSL2 (VPN workaround using wsl-vpnkit)
# Run: wsl -d Debian -- bash /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/.setup_wsl_codex.sh
# Updated: 2026-03-08
#
# Prerequisites:
#   wsl --import wsl-vpnkit --version 2 $env:USERPROFILE\wsl-vpnkit wsl-vpnkit.tar.gz
#   (download from https://github.com/sakai135/wsl-vpnkit/releases)

set -euo pipefail

echo "=== WSL2 VPN Fix (wsl-vpnkit) ==="

# 1. Check if wsl-vpnkit distro exists and start it
echo ""
echo "Step 1: Starting wsl-vpnkit..."
if wsl.exe -d wsl-vpnkit -- echo "ok" >/dev/null 2>&1; then
  # Check if already running (tap device exists)
  if ip link show wsltap >/dev/null 2>&1; then
    echo "  wsl-vpnkit already running (wsltap present)"
  else
    echo "  Launching wsl-vpnkit in background..."
    # Start wsl-vpnkit from Windows side (it needs to run in its own distro)
    wsl.exe -d wsl-vpnkit -- /app/wsl-vpnkit &
    sleep 5
    echo "  wsl-vpnkit started"
  fi
else
  echo "  ERROR: wsl-vpnkit distro not found!"
  echo "  Install it first:"
  echo "    1. Download: https://github.com/sakai135/wsl-vpnkit/releases/download/v0.4.1/wsl-vpnkit.tar.gz"
  echo "    2. Import:   wsl --import wsl-vpnkit --version 2 \$USERPROFILE\\wsl-vpnkit wsl-vpnkit.tar.gz"
  exit 1
fi

# 2. Configure DNS
echo ""
echo "Step 2: Configuring DNS..."
echo "nameserver 172.26.16.1" > /etc/resolv.conf
echo "  Set nameserver to 172.26.16.1"

# 3. Connectivity check
echo ""
echo "Step 3: Connectivity check..."
OK=0
FAIL=0
for domain in api.openai.com auth0.openai.com; do
  HTTP_CODE=$(curl -so /dev/null --connect-timeout 5 -w '%{http_code}' "https://$domain" 2>/dev/null || echo "000")
  if [[ "$HTTP_CODE" != "000" ]]; then
    echo "  OK   $domain (HTTP $HTTP_CODE)"
    ((OK++))
  else
    echo "  FAIL $domain"
    ((FAIL++))
  fi
done

echo ""
if [[ $FAIL -eq 0 ]]; then
  echo "All checks passed. Codex CLI should work now."
  echo "Run: codex"
else
  echo "Some checks failed. wsl-vpnkit may need more time to start."
  echo "Retry in a few seconds or check: wsl -d wsl-vpnkit -- /app/wsl-vpnkit"
fi
