#!/usr/bin/env bash
# Stop shared MCP plane (Linux/WSL).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
PID_DIR="$ROOT/logs/mcp-shared/pids"
if [[ ! -d "$PID_DIR" ]]; then
  echo "No pid dir: $PID_DIR"
  exit 0
fi
for f in "$PID_DIR"/*.pid; do
  [[ -f "$f" ]] || continue
  pid="$(tr -d ' \n\r' <"$f" || true)"
  name="$(basename "$f" .pid)"
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
