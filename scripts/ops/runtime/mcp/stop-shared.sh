#!/usr/bin/env bash
# Stop shared MCP plane (Linux/WSL).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
PID_DIR="$ROOT/logs/mcp-shared/pids"
if [[ -n "${WSL_INTEROP:-}" ]] || grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null; then
  "/mnt/c/Users/Fedor/AppData/Local/Programs/Python/Python313/python.exe" -B \
    "D:/pc-agent/tools/shared-mcp/service-owner.py" context7 stop
fi
if [[ ! -d "$PID_DIR" ]]; then
  echo "No pid dir: $PID_DIR"
  exit 0
fi
for f in "$PID_DIR"/*.pid; do
  [[ -f "$f" ]] || continue
  pid="$(tr -d ' \n\r' <"$f" || true)"
  name="$(basename "$f" .pid)"
  if [[ "$name" == "context7" ]] && { [[ -n "${WSL_INTEROP:-}" ]] || grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null; }; then
    echo "Context7 is owned by Windows; preserving the old Linux PID record."
    continue
  fi
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    echo "Stopping $name pid=$pid"
    # start-shared creates a dedicated process group per logical server.
    kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
    for _ in {1..20}; do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.25
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 -- "-$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
    fi
  fi
  rm -f "$f"
done
echo "stop-shared done."
