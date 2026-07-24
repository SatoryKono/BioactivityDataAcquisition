#!/usr/bin/env bash
# Start shared MCP plane (Linux/WSL). See start-shared.ps1 for Windows.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"
CATALOG="$ROOT/scripts/ops/runtime/mcp/shared-servers.json"
LOG_DIR="$ROOT/logs/mcp-shared"
PID_DIR="$LOG_DIR/pids"
mkdir -p "$PID_DIR"
PROXY_PKG="$(python -c "import json; print(json.load(open('$CATALOG'))['proxy_package'])")"
python - <<'PY' "$CATALOG" "$ROOT" "$PID_DIR" "$PROXY_PKG"
import json, os, socket, subprocess, sys, time
from pathlib import Path

catalog_path, root, pid_dir, proxy_pkg = sys.argv[1:5]
catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
root = Path(root)
pid_dir = Path(pid_dir)
status = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "proxy_package": proxy_pkg, "servers": {}}

def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except OSError:
            return False

for name, entry in catalog["servers"].items():
    port = int(entry["port"])
    wrapper = root / "scripts/ai/mcp" / f"{entry['wrapper']}.sh"
    if not wrapper.is_file():
        print(f"skip {name}: missing {wrapper}", file=sys.stderr)
        continue
    if port_open(port):
        print(f"OK already listening 127.0.0.1:{port} ({name})")
        status["servers"][name] = {"port": port, "state": "already_up"}
        continue
    log_out = root / "logs/mcp-shared" / f"{name}.out.log"
    log_err = root / "logs/mcp-shared" / f"{name}.err.log"
    log_out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "npx", "-y", proxy_pkg,
        "--port", str(port),
        "--server", "stream",
        "--",
        "bash", str(wrapper),
    ]
    print(f"Starting shared MCP {name} on 127.0.0.1:{port} ...")
    with open(log_out, "ab") as out, open(log_err, "ab") as err:
        proc = subprocess.Popen(cmd, cwd=str(root), stdout=out, stderr=err)
    (pid_dir / f"{name}.pid").write_text(str(proc.pid), encoding="ascii")
    time.sleep(0.8)
    state = "started" if port_open(port) else "starting"
    status["servers"][name] = {
        "port": port,
        "state": state,
        "pid": proc.pid,
        "url": f"http://127.0.0.1:{port}{entry.get('path', '/mcp')}",
    }
    print(f"  pid={proc.pid} state={state}")

status_path = root / "logs/mcp-shared/status.json"
status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {status_path}")
PY
