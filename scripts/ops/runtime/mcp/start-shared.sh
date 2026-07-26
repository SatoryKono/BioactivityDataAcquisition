#!/usr/bin/env bash
# Start shared MCP plane (Linux/WSL). See start-shared.ps1 for Windows.
<<<<<<< Updated upstream
# Sequential start, pre-warm mcp-proxy, longer settle for docker-backed servers.
||||||| Stash base
=======
# W1.2: sequential start, pre-warm mcp-proxy, dedicated npm cache, one retry.
>>>>>>> Stashed changes
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"
CATALOG="$ROOT/scripts/ops/runtime/mcp/shared-servers.json"
LOG_DIR="$ROOT/logs/mcp-shared"
PID_DIR="$LOG_DIR/pids"
<<<<<<< Updated upstream
NPM_CACHE="$LOG_DIR/npm-cache"
mkdir -p "$PID_DIR" "$NPM_CACHE"
export NPM_CONFIG_CACHE="$NPM_CACHE"
PROXY_PKG="$(python3 -c "import json; print(json.load(open(r'$CATALOG'))['proxy_package'])")"
SETTLE="${SETTLE_SECONDS:-12}"
DOCKER_SETTLE="${DOCKER_SETTLE_SECONDS:-45}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-2}"

# Optional subset: start-shared.sh brave-search grafana prometheus
SELECTED=("$@")

echo "Pre-warming $PROXY_PKG ..."
npx -y "$PROXY_PKG" --help >/dev/null 2>"$LOG_DIR/prewarm.err.log" || echo "pre-warm warning (see prewarm.err.log)"

python3 - <<'PY' "$CATALOG" "$ROOT" "$PID_DIR" "$PROXY_PKG" "$SETTLE" "$DOCKER_SETTLE" "$MAX_ATTEMPTS" "$NPM_CACHE" "${SELECTED[@]}"
||||||| Stash base
mkdir -p "$PID_DIR"
PROXY_PKG="$(python -c "import json; print(json.load(open('$CATALOG'))['proxy_package'])")"
python - <<'PY' "$CATALOG" "$ROOT" "$PID_DIR" "$PROXY_PKG"
=======
NPM_CACHE="$LOG_DIR/npm-cache"
mkdir -p "$PID_DIR" "$NPM_CACHE"
export NPM_CONFIG_CACHE="$NPM_CACHE"
PROXY_PKG="$(python -c "import json; print(json.load(open(r'$CATALOG'))['proxy_package'])")"
SETTLE="${SETTLE_SECONDS:-12}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-2}"

echo "Pre-warming $PROXY_PKG ..."
npx -y "$PROXY_PKG" --help >/dev/null 2>"$LOG_DIR/prewarm.err.log" || echo "pre-warm warning (see prewarm.err.log)"

python - <<'PY' "$CATALOG" "$ROOT" "$PID_DIR" "$PROXY_PKG" "$SETTLE" "$MAX_ATTEMPTS" "$NPM_CACHE"
>>>>>>> Stashed changes
import json, os, socket, subprocess, sys, time
from pathlib import Path

<<<<<<< Updated upstream
catalog_path, root, pid_dir, proxy_pkg, settle, docker_settle, max_attempts, npm_cache = sys.argv[1:9]
selected = sys.argv[9:]
||||||| Stash base
catalog_path, root, pid_dir, proxy_pkg = sys.argv[1:5]
=======
catalog_path, root, pid_dir, proxy_pkg, settle, max_attempts, npm_cache = sys.argv[1:8]
>>>>>>> Stashed changes
catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
root = Path(root)
pid_dir = Path(pid_dir)
<<<<<<< Updated upstream
settle = int(settle)
docker_settle = int(docker_settle)
max_attempts = max(1, int(max_attempts))
os.environ["NPM_CONFIG_CACHE"] = npm_cache
status = {
    "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "proxy_package": proxy_pkg,
    "npm_cache": npm_cache,
    "servers": {},
}
failed = 0

# Docker-backed thrash leaders need longer cold-start.
DOCKER_HEAVY = frozenset({"brave-search", "prometheus", "grafana", "docker", "mermaid", "dockerhub"})
||||||| Stash base
status = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "proxy_package": proxy_pkg, "servers": {}}
=======
settle = int(settle)
max_attempts = max(1, int(max_attempts))
os.environ["NPM_CONFIG_CACHE"] = npm_cache
status = {
    "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "proxy_package": proxy_pkg,
    "npm_cache": npm_cache,
    "servers": {},
}
failed = 0
>>>>>>> Stashed changes

def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except OSError:
            return False

<<<<<<< Updated upstream
items = sorted(
    catalog["servers"].items(),
    key=lambda kv: (int(kv[1].get("priority", 100)), kv[0]),
)
if selected:
    allow = set(selected)
    items = [(n, e) for n, e in items if n in allow]
    missing = allow - {n for n, _ in items}
    for name in sorted(missing):
        print(f"skip unknown server {name}", file=sys.stderr)
        failed += 1

for name, entry in items:
||||||| Stash base
for name, entry in catalog["servers"].items():
=======
items = sorted(
    catalog["servers"].items(),
    key=lambda kv: (int(kv[1].get("priority", 100)), kv[0]),
)

for name, entry in items:
>>>>>>> Stashed changes
    port = int(entry["port"])
    wrapper = root / "scripts/ai/mcp" / f"{entry['wrapper']}.sh"
    if not wrapper.is_file():
        # fall back to .ps1 not available on bash path
        print(f"skip {name}: missing {wrapper}", file=sys.stderr)
        failed += 1
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
<<<<<<< Updated upstream
    server_settle = docker_settle if name in DOCKER_HEAVY else settle
    state = "exited"
    last_pid = None
    for attempt in range(1, max_attempts + 1):
        print(
            f"Starting shared MCP {name} on 127.0.0.1:{port} "
            f"(attempt {attempt}/{max_attempts}, settle={server_settle}s) ..."
        )
        with open(log_out, "ab") as out, open(log_err, "ab") as err:
            proc = subprocess.Popen(
                cmd, cwd=str(root), stdout=out, stderr=err, env=os.environ.copy()
            )
        last_pid = proc.pid
        (pid_dir / f"{name}.pid").write_text(str(proc.pid), encoding="ascii")
        deadline = time.time() + max(5, server_settle)
        state = "starting"
        while time.time() < deadline:
            time.sleep(0.5)
            if port_open(port):
                state = "started"
                break
            if proc.poll() is not None:
                state = "exited"
                break
        if state == "started":
            break
        if attempt < max_attempts:
            print(f"  retry {name} after failure state={state}", file=sys.stderr)
            try:
                proc.terminate()
            except Exception:
                pass
            time.sleep(2)

||||||| Stash base
    print(f"Starting shared MCP {name} on 127.0.0.1:{port} ...")
    with open(log_out, "ab") as out, open(log_err, "ab") as err:
        proc = subprocess.Popen(cmd, cwd=str(root), stdout=out, stderr=err)
    (pid_dir / f"{name}.pid").write_text(str(proc.pid), encoding="ascii")
    time.sleep(0.8)
    state = "started" if port_open(port) else "starting"
=======
    state = "exited"
    last_pid = None
    for attempt in range(1, max_attempts + 1):
        print(f"Starting shared MCP {name} on 127.0.0.1:{port} (attempt {attempt}/{max_attempts}) ...")
        with open(log_out, "wb") as out, open(log_err, "wb") as err:
            proc = subprocess.Popen(cmd, cwd=str(root), stdout=out, stderr=err, env=os.environ.copy())
        last_pid = proc.pid
        (pid_dir / f"{name}.pid").write_text(str(proc.pid), encoding="ascii")
        deadline = time.time() + max(5, settle)
        state = "starting"
        while time.time() < deadline:
            time.sleep(0.5)
            if port_open(port):
                state = "started"
                break
            if proc.poll() is not None:
                state = "exited"
                break
        if state == "started":
            break
        if attempt < max_attempts:
            print(f"  retry {name} after failure state={state}", file=sys.stderr)
            time.sleep(2)

>>>>>>> Stashed changes
    status["servers"][name] = {
        "port": port,
        "state": state,
        "pid": last_pid,
        "url": f"http://127.0.0.1:{port}{entry.get('path', '/mcp')}",
    }
<<<<<<< Updated upstream
    print(f"  pid={last_pid} state={state}")
    if state != "started":
        failed += 1
||||||| Stash base
    print(f"  pid={proc.pid} state={state}")
=======
    print(f"  pid={last_pid} state={state}")
    if state == "exited":
        failed += 1
>>>>>>> Stashed changes

status_path = root / "logs/mcp-shared/status.json"
status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {status_path}")
sys.exit(1 if failed else 0)
PY
