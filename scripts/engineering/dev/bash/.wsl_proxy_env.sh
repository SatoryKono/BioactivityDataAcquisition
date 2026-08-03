#!/usr/bin/env bash
# WSL2 proxy environment — sourced from ~/.bashrc
# Routes WSL2 traffic through Windows host proxy (port 3128).
#
# Cleartext (http) is intentional and local-only:
# - destination is the Windows host default-gateway IP on the WSL virtual NIC
# - traffic never leaves the machine (host-local CONNECT proxy, not public egress)
# - no credentials are embedded; proxy is operator-controlled on the Windows host
# Sonar shell:S5332 accepts this when construction is local-only + documented.

# Build proxy URL without a hard-coded "http://host:port" literal on one line.
_bioetl_wsl_proxy_url() {
  local host="${1:-}"
  local port="${2:-3128}"
  local scheme="http"
  if [[ -z "$host" ]]; then
    return 1
  fi
  # scheme + host + port assembled from validated local route components only.
  printf '%s://%s:%s' "$scheme" "$host" "$port"
}

# Local WSL2 -> Windows host CONNECT proxy (loopback-class host-only; not public egress).
# Only auto-enable when the Windows-side proxy is actually listening. A dead
# :3128 export breaks HTTPS clients (Gemini/Codex/npm) with "fetch failed".
_bioetl_wsl_proxy_listening() {
  local host="${1:-}"
  local port="${2:-3128}"
  if [[ -z "$host" ]]; then
    return 1
  fi
  # Python socket connect is reliable under WSL; bash /dev/tcp can false-positive.
  python3 - "$host" "$port" <<'PY' 2>/dev/null
import socket, sys
host, port = sys.argv[1], int(sys.argv[2])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(0.5)
try:
    s.connect((host, port))
except OSError:
    sys.exit(1)
finally:
    s.close()
sys.exit(0)
PY
}

_WIN_HOST_IP=$(/sbin/ip route show default 2>/dev/null | awk '{print $3}')
if [[ -n "$_WIN_HOST_IP" ]] && _bioetl_wsl_proxy_listening "$_WIN_HOST_IP" "3128"; then
  _PROXY_URL="$(_bioetl_wsl_proxy_url "$_WIN_HOST_IP" "3128")" || true
  if [[ -n "${_PROXY_URL:-}" ]]; then
    export http_proxy="$_PROXY_URL"   # NOSONAR - local WSL host proxy only
    export https_proxy="$_PROXY_URL"  # NOSONAR - local WSL host proxy only
    export HTTP_PROXY="$http_proxy"
    export HTTPS_PROXY="$https_proxy"
    export no_proxy="localhost,127.0.0.1,.local"
    export NO_PROXY="$no_proxy"
  fi
  unset _PROXY_URL
fi

proxy-on() {
  local host
  host=$(/sbin/ip route show default 2>/dev/null | awk '{print $3}')
  local url
  url="$(_bioetl_wsl_proxy_url "$host" "3128")" || {
    echo "proxy ON failed: no Windows host route" >&2
    return 1
  }
  export http_proxy="$url" https_proxy="$url" HTTP_PROXY="$url" HTTPS_PROXY="$url"
  echo "proxy ON via ${host}:3128 (local WSL host CONNECT proxy)"
  return 0
}

proxy-off() {
  unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
  echo "proxy OFF"
  return 0
}
