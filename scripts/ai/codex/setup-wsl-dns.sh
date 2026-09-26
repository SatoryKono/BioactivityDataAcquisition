#!/usr/bin/env bash
# Optional WSL DNS helper for Codex device-auth.
# Default is dry-run. Host writes require an explicit --apply.
set -euo pipefail

BANNER_LINE='========================================'
APPLY=0
WSL_USER="${WSL_USER:-${USER:-}}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/ai/codex/setup-wsl-dns.sh           # dry-run (default)
  bash scripts/ai/codex/setup-wsl-dns.sh --dry-run
  bash scripts/ai/codex/setup-wsl-dns.sh --apply

Rewrites /etc/wsl.conf and /etc/resolv.conf for static Google DNS.
Does not run without --apply. Set WSL_USER to override the wsl.conf default user.
EOF
}

for arg in "$@"; do
  case "${arg}" in
    --apply) APPLY=1 ;;
    --dry-run) APPLY=0 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown option: ${arg}" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${WSL_USER}" ]]; then
  echo "ERROR: WSL_USER / USER is empty; refuse to write a hardcoded username." >&2
  exit 1
fi

if ! grep -qi microsoft /proc/version 2>/dev/null; then
  echo "ERROR: This script must be run in WSL" >&2
  exit 1
fi

echo "${BANNER_LINE}"
echo "WSL DNS Setup for Codex Device Auth"
echo "${BANNER_LINE}"
if [[ "${APPLY}" -eq 0 ]]; then
  echo "Mode: dry-run (no host writes). Pass --apply to change /etc."
else
  echo "Mode: apply (will write /etc/wsl.conf and /etc/resolv.conf)"
fi
echo "wsl.conf default user: ${WSL_USER}"
echo ""

if [[ "${APPLY}" -eq 0 ]]; then
  echo "Would write /etc/wsl.conf [network] generateResolvConf=false and default=${WSL_USER}"
  echo "Would write /etc/resolv.conf nameserver 8.8.8.8 / 8.8.4.4"
  echo "Would run: sudo chattr +i /etc/resolv.conf"
  echo "Would ping auth.openai.com"
  exit 0
fi

echo "Step 1: Configuring /etc/wsl.conf..."
sudo tee /etc/wsl.conf >/dev/null <<EOF
[boot]
systemd=true

[user]
default=${WSL_USER}

[network]
generateResolvConf = false
EOF

echo "Step 2: Configuring /etc/resolv.conf with Google DNS..."
sudo tee /etc/resolv.conf >/dev/null <<'EOF'
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF

echo "Step 3: Protecting /etc/resolv.conf from overwrites..."
sudo chattr +i /etc/resolv.conf

echo "Step 4: Testing DNS resolution..."
if ping -c 1 -W 2 auth.openai.com > /dev/null 2>&1; then
  echo "DNS resolution working for auth.openai.com"
else
  echo "WARNING: DNS resolution still failing for auth.openai.com" >&2
fi

echo "${BANNER_LINE}"
echo "DNS Setup Complete"
echo "Undo: sudo chattr -i /etc/resolv.conf ; restore /etc/wsl.conf ; restart WSL"
