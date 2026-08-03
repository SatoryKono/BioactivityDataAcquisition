#!/usr/bin/env bash
# Probe shared MCP plane ports (Linux/WSL).
# Exit 1 only when a *daily* (or selected) server is DOWN.
# Optional servers (daily=false) report WARN and do not fail the gate.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
CATALOG="$ROOT/scripts/ops/runtime/mcp/shared-servers.json"
MODE="${1:-daily}"  # daily | all
python3 - <<'PY' "$CATALOG" "$ROOT" "$MODE"
import json, socket, sys, time, urllib.request
from pathlib import Path

catalog = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
root = Path(sys.argv[2])
mode = sys.argv[3]
failed = 0
warned = 0
results = []

def port_open(port: int, timeout: float = 1.0) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except OSError:
            return False

for name, entry in sorted(catalog["servers"].items(), key=lambda kv: kv[0]):
    port = int(entry["port"])
    path = entry.get("path") or "/mcp"
    url = f"http://127.0.0.1:{port}{path}"
    is_daily = entry.get("daily", True) is not False
    required = mode == "all" or is_daily
    up = port_open(port, timeout=1.0)
    ping_ok = False
    if up:
        if entry.get("launch_mode") == "windows_docker_streaming":
            ping_ok = True
        else:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/ping", timeout=2) as r:
                    ping_ok = 200 <= r.status < 500
            except Exception:
                ping_ok = False
    ready = up and ping_ok
    if not ready and required:
        failed += 1
        mark = "DOWN"
    elif not ready:
        warned += 1
        mark = "WARN"
    else:
        mark = "OK"
    print(f"[{mark}] {name} port={up} ping={ping_ok} daily={is_daily} {url}")
    results.append(
        {
            "server": name,
            "port": port,
            "url": url,
            "port_open": up,
            "ping_ok": ping_ok,
            "ready": ready,
            "daily": is_daily,
            "required": required,
            "status": mark,
        }
    )

out = root / "logs/mcp-shared/health.json"
out.parent.mkdir(parents=True, exist_ok=True)
payload = json.dumps(
    {
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": mode,
        "failed": failed,
        "warned": warned,
        "results": results,
    },
    indent=2,
) + "\n"
temp = out.with_suffix(out.suffix + ".tmp")
temp.write_text(payload, encoding="utf-8")
temp.replace(out)
print(f"Wrote {out} failed={failed} warned={warned}")
sys.exit(1 if failed else 0)
PY
