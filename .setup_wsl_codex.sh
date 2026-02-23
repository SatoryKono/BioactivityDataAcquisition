#!/bin/bash
# Setup script for Codex in WSL Debian
# Run: wsl -d Debian -- bash /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/.setup_wsl_codex.sh

# Ensure OpenAI DNS entries in /etc/hosts (workaround for VPN DNS flakiness)
ensure_host() {
  local domain=$1
  if ! grep -q "$domain" /etc/hosts 2>/dev/null; then
    local ip
    ip=$(getent hosts "$domain" 2>/dev/null | awk '{print $1}' | head -1)
    if [ -n "$ip" ]; then
      echo "$ip $domain" >> /etc/hosts
    fi
  fi
}
ensure_host api.openai.com
ensure_host auth0.openai.com
ensure_host auth.openai.com
ensure_host developers.openai.com

echo "OpenAI DNS hosts configured."
grep openai /etc/hosts
