#!/bin/bash
/# Fix OpenAI DNS in WSL2 (VPN workaround)
# Run: bash /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/.setup_wsl_codex.sh

ensure_host() {
  local domain=$1
  local fallback_ip=$2
  if ! grep -q "$domain" /etc/hosts 2>/dev/null; then
    local ip
    ip=$(getent hosts "$domain" 2>/dev/null | awk '{print $1}' | head -1)
    ip=${ip:-$fallback_ip}
    if [ -n "$ip" ]; then
      echo "$ip $domain" >> /etc/hosts
      echo "  + $domain -> $ip"
    else
      echo "  ! $domain — не удалось резолвить, fallback IP не задан"
    fi
  fi
}

echo "Configuring OpenAI DNS hosts..."
ensure_host chatgpt.com             104.18.32.47
ensure_host api.openai.com          162.159.140.245
ensure_host auth.openai.com         104.18.41.241
ensure_host auth0.openai.com        172.65.90.22
ensure_host developers.openai.com   64.239.109.193

echo "Done. Current entries:"
grep -E "openai|chatgpt" /etc/hosts
