#!/usr/bin/env bash
# Resolve OpenAI + npm hosts and cache IPv4 in /etc/hosts (VPN workaround)
# Called from ~/.bashrc if api.openai.com is missing from /etc/hosts
#
# Strategy: try dig first (fast), fallback to Windows Resolve-DnsName via
# powershell.exe (works even when WSL2 DNS is broken by VPN).

set -euo pipefail

HOSTS=(
  api.openai.com
  auth0.openai.com
  auth.openai.com
  cdn.openai.com
  developers.openai.com
  registry.npmjs.org
)

MARKER="# OpenAI + npm DNS (VPN workaround)"

# --- resolve helpers ---------------------------------------------------

resolve_dig() {
  dig +short "$1" 2>/dev/null | grep -E '^[0-9]+\.' | head -1 || true
}

resolve_powershell() {
  # Ask Windows DNS via interop; filter Type-A records (skip CNAMEs)
  powershell.exe -NoProfile -Command \
    "try { (Resolve-DnsName -Name '$1' -Type A -ErrorAction Stop | Where-Object { \$_.QueryType -eq 'A' } | Select-Object -First 1).IPAddress } catch {}" \
    2>/dev/null | tr -d '\r' | grep -E '^[0-9]+\.' | head -1 || true
}

resolve_host() {
  local ip
  ip=$(resolve_dig "$1")
  if [ -z "$ip" ]; then
    ip=$(resolve_powershell "$1")
  fi
  echo "$ip"
}

# --- main --------------------------------------------------------------

TMPFILE=$(mktemp)

# Keep everything except old OpenAI/npm DNS block
grep -v "openai.com\|registry.npmjs.org\|# OpenAI.*DNS" /etc/hosts > "$TMPFILE" 2>/dev/null || true

echo "$MARKER" >> "$TMPFILE"

ok=0
fail=0
for host in "${HOSTS[@]}"; do
  ip=$(resolve_host "$host")
  if [ -n "$ip" ]; then
    echo "$ip $host" >> "$TMPFILE"
    echo "  resolved: $host -> $ip"
    ok=$((ok + 1))
  else
    echo "  WARN: could not resolve $host"
    fail=$((fail + 1))
  fi
done

if [ "$ok" -gt 0 ]; then
  cp "$TMPFILE" /etc/hosts
  echo "DNS cache updated ($ok resolved, $fail failed)"
else
  echo "ERROR: no hosts resolved — /etc/hosts NOT modified"
fi

rm -f "$TMPFILE"
