#!/usr/bin/env bash
# Probe shared MCP plane ports (Linux/WSL). W1.3: hard timeouts.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
CATALOG="$ROOT/scripts/ops/runtime/mcp/shared-servers.json"
<<<<<<< Updated upstream
python3 - <<'PY' "$CATALOG" "$ROOT"
||||||| Stash base
python - <<'PY' "$CATALOG" "$ROOT"
=======
TIMEOUT="${TIMEOUT_SEC:-3}"
OVERALL="${OVERALL_TIMEOUT_SEC:-45}"
python - <<'PY' "$CATALOG" "$ROOT" "$TIMEOUT" "$OVERALL"
>>>>>>> Stashed changes
import json, socket, sys, time, urllib.request
from pathlib import Path

catalog = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
root = Path(sys.argv[2])
timeout = max(1, int(sys.argv[3]))
overall = max(5, int(sys.argv[4]))
failed = 0
results = []
started = time.time()
deadline = started + overall

def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(float(timeout))
        try:
            s.connect(("127.0.0.1", port))
            return True
        except OSError:
            return False

for name, entry in catalog["servers"].items():
    if time.time() > deadline:
        print(f"[DOWN] {name} overall_timeout", flush=True)
        failed += 1
        results.append({"server": name, "ok": False, "error": "overall_timeout"})
        continue
    port = int(entry["port"])
    path = entry.get("path") or "/mcp"
    url = f"http://127.0.0.1:{port}{path}"
    up = port_open(port)
    ping_ok = False
    if up:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/ping", timeout=timeout) as r:
                ping_ok = 200 <= r.status < 500
        except Exception:
            ping_ok = False
    if not up:
        failed += 1
    mark = "OK" if up else "DOWN"
    print(f"[{mark}] {name} port={up} ping={ping_ok} {url}")
    results.append({"server": name, "port": port, "url": url, "port_open": up, "ping_ok": ping_ok})

elapsed = round(time.time() - started, 2)
out = root / "logs/mcp-shared/health.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    json.dumps(
        {
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "failed": failed,
            "timeout_sec": timeout,
            "overall_timeout_sec": overall,
            "elapsed_sec": elapsed,
            "results": results,
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
print(f"health-shared: failed={failed} elapsed={elapsed}s")
sys.exit(1 if failed else 0)
PY
