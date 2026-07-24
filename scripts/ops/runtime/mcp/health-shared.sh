#!/usr/bin/env bash
# Probe shared MCP plane ports (Linux/WSL).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
CATALOG="$ROOT/scripts/ops/runtime/mcp/shared-servers.json"
python - <<'PY' "$CATALOG" "$ROOT"
import json, socket, sys, time, urllib.request
from pathlib import Path

catalog = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
root = Path(sys.argv[2])
failed = 0
results = []

def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except OSError:
            return False

for name, entry in catalog["servers"].items():
    port = int(entry["port"])
    path = entry.get("path") or "/mcp"
    url = f"http://127.0.0.1:{port}{path}"
    up = port_open(port)
    ping_ok = False
    if up:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/ping", timeout=2) as r:
                ping_ok = 200 <= r.status < 500
        except Exception:
            ping_ok = False
    if not up:
        failed += 1
    mark = "OK" if up else "DOWN"
    print(f"[{mark}] {name} port={up} ping={ping_ok} {url}")
    results.append({"server": name, "port": port, "url": url, "port_open": up, "ping_ok": ping_ok})

out = root / "logs/mcp-shared/health.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "failed": failed, "results": results}, indent=2) + "\n", encoding="utf-8")
sys.exit(1 if failed else 0)
PY
