#!/bin/bash
# Fix OpenAI DNS in WSL2 (VPN workaround)
# Run: bash /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/.setup_wsl_codex.sh
# Use --force to refresh stale IPs: bash .setup_wsl_codex.sh --force
# Updated: 2026-03-02

FORCE=0
[[ "$1" == "--force" ]] && FORCE=1

# Domain -> IPv4 mapping (resolved from Windows host 2026-03-02, refreshed)
declare -A HOSTS=(
  [api.openai.com]=172.66.0.243
  [auth.openai.com]=104.18.41.241
  [auth0.openai.com]=172.65.90.22
  [chatgpt.com]=104.18.32.47
  [developers.openai.com]=64.239.109.1
  [cdn.openai.com]=104.18.41.241
  [files.oaiusercontent.com]=104.18.41.241
)

echo "Configuring OpenAI DNS hosts..."

if [[ $FORCE -eq 1 ]]; then
  sed -i '/openai\|chatgpt/d' /etc/hosts
  echo "  Cleared all old OpenAI/ChatGPT entries"
fi

for domain in "${!HOSTS[@]}"; do
  ip="${HOSTS[$domain]}"
  if grep -q "$domain" /etc/hosts 2>/dev/null; then
    echo "  = $domain — already present (use --force to refresh)"
  else
    echo "$ip $domain" >> /etc/hosts
    echo "  + $domain -> $ip"
  fi
done

echo ""
echo "Current /etc/hosts entries:"
grep -E "openai|chatgpt" /etc/hosts

echo ""
echo "Quick connectivity check..."
for domain in api.openai.com auth0.openai.com; do
  if curl -so /dev/null --connect-timeout 5 "https://$domain" 2>/dev/null; then
    echo "  OK   $domain"
  else
    echo "  FAIL $domain"
  fi
done
