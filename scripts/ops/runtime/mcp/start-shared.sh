#!/usr/bin/env bash
# Start the singleton shared MCP plane on Linux/WSL.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"
CATALOG="$ROOT/scripts/ops/runtime/mcp/shared-servers.json"
LOG_DIR="$ROOT/logs/mcp-shared"
PID_DIR="$LOG_DIR/pids"
NPM_CACHE="$LOG_DIR/npm-cache"
UV_CACHE="${UV_CACHE_DIR:-/tmp/bioetl-mcp-uv-cache}"
UV_TOOLS="${UV_TOOL_DIR:-/tmp/bioetl-mcp-uv-tools}"
mkdir -p "$PID_DIR" "$NPM_CACHE" "$UV_CACHE" "$UV_TOOLS"

# One launcher owns reconciliation at a time. Child processes do not inherit
# this descriptor because Python Popen closes unrelated file descriptors.
exec 9>"$PID_DIR/launcher.lock"
flock 9

export NPM_CONFIG_CACHE="$NPM_CACHE"
export UV_CACHE_DIR="$UV_CACHE"
export UV_TOOL_DIR="$UV_TOOLS"

MODE="daily"
SELECTED=()
for arg in "$@"; do
  case "$arg" in
    --all|-a) MODE="all" ;;
    --daily|-d) MODE="daily" ;;
    *) SELECTED+=("$arg") ;;
  esac
done

PROXY_PKG="$(python3 -c "import json; print(json.load(open(r'$CATALOG'))['proxy_package'])")"
echo "Pre-warming $PROXY_PKG ..."
npx -y "$PROXY_PKG" --help >"$LOG_DIR/prewarm.out.log" 2>"$LOG_DIR/prewarm.err.log" || \
  echo "pre-warm warning (see $LOG_DIR/prewarm.err.log)"

python3 - "$CATALOG" "$ROOT" "$PID_DIR" "$LOG_DIR" "$MODE" "${SELECTED[@]}" <<'PY'
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

catalog_path, root_arg, pid_arg, log_arg, mode, *selected = sys.argv[1:]
catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
root = Path(root_arg)
pid_dir = Path(pid_arg)
log_dir = Path(log_arg)
proxy_package = str(catalog["proxy_package"])
bind_host = str(catalog.get("bind_host") or "127.0.0.1")
connection_timeout_ms = int(catalog.get("connection_timeout_ms") or 180_000)
request_timeout_ms = int(catalog.get("request_timeout_ms") or 300_000)

if bind_host not in {"127.0.0.1", "localhost"}:
    raise SystemExit(f"refusing non-loopback shared MCP bind host: {bind_host}")


def port_open(port: int, timeout: float = 0.3) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect(("127.0.0.1", port))
            return True
        except OSError:
            return False


def ping_ready(port: int, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/ping", timeout=timeout
        ) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def read_pid(path: Path) -> int | None:
    try:
        value = int(path.read_text(encoding="ascii").strip())
        os.kill(value, 0)
        return value
    except (OSError, ValueError):
        return None


def atomic_text(path: Path, value: str) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(value, encoding="utf-8")
    os.replace(temp, path)


def stop_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


items = sorted(
    catalog["servers"].items(),
    key=lambda item: (int(item[1].get("priority", 100)), item[0]),
)
if selected:
    wanted = set(selected)
    known = {name for name, _ in items}
    unknown = sorted(wanted - known)
    if unknown:
        raise SystemExit(f"unknown shared MCP servers: {', '.join(unknown)}")
    items = [(name, entry) for name, entry in items if name in wanted]
elif mode == "daily":
    items = [
        (name, entry)
        for name, entry in items
        if entry.get("daily", True) is not False
    ]

status: dict[str, object] = {
    "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "proxy_package": proxy_package,
    "bind_host": bind_host,
    "mode": mode,
    "servers": {},
}
server_status: dict[str, dict[str, object]] = status["servers"]  # type: ignore[assignment]
pending: dict[str, tuple[subprocess.Popen[bytes], float, object, object]] = {}
failed = 0

for name, entry in items:
    port = int(entry["port"])
    path = str(entry.get("path") or "/mcp")
    url = f"http://127.0.0.1:{port}{path}"
    wrapper = root / "scripts/ai/mcp" / f"{entry['wrapper']}.sh"
    pid_path = pid_dir / f"{name}.pid"

    if not wrapper.is_file():
        print(f"FAIL {name}: missing wrapper {wrapper}", file=sys.stderr)
        server_status[name] = {"port": port, "url": url, "state": "missing_wrapper"}
        failed += 1
        continue
    if ping_ready(port):
        existing_pid = read_pid(pid_path)
        print(f"OK already ready 127.0.0.1:{port} ({name}) pid={existing_pid}")
        server_status[name] = {
            "port": port,
            "url": url,
            "state": "already_up",
            "pid": existing_pid,
        }
        continue
    if port_open(port):
        print(
            f"FAIL {name}: port {port} belongs to a non-ready/foreign listener",
            file=sys.stderr,
        )
        server_status[name] = {"port": port, "url": url, "state": "foreign_port"}
        failed += 1
        continue

    stale_pid = read_pid(pid_path)
    if stale_pid is not None:
        # A managed process may still be initializing without a listener.
        # Never launch a competitor; wait for its full readiness deadline.
        print(f"WAIT managed process {name} pid={stale_pid}")
        server_status[name] = {
            "port": port,
            "url": url,
            "state": "starting_existing",
            "pid": stale_pid,
        }
        deadline = time.monotonic() + int(entry.get("readiness_timeout_sec") or 180)
        pending[name] = (None, deadline, None, None)  # type: ignore[assignment]
        continue

    out_path = log_dir / f"{name}.out.log"
    err_path = log_dir / f"{name}.err.log"
    out_handle = out_path.open("ab")
    err_handle = err_path.open("ab")
    command = [
        "npx",
        "-y",
        proxy_package,
        "--host",
        bind_host,
        "--port",
        str(port),
        "--server",
        "stream",
        "--connectionTimeout",
        str(connection_timeout_ms),
        "--requestTimeout",
        str(request_timeout_ms),
        "--",
        "bash",
        str(wrapper),
    ]
    print(f"START {name} 127.0.0.1:{port}")
    process = subprocess.Popen(
        command,
        cwd=root,
        env=os.environ.copy(),
        stdout=out_handle,
        stderr=err_handle,
        start_new_session=True,
        close_fds=True,
    )
    atomic_text(pid_path, f"{process.pid}\n")
    deadline = time.monotonic() + int(entry.get("readiness_timeout_sec") or 180)
    pending[name] = (process, deadline, out_handle, err_handle)
    server_status[name] = {
        "port": port,
        "url": url,
        "state": "starting",
        "pid": process.pid,
    }

while pending:
    now = time.monotonic()
    for name in list(pending):
        process, deadline, out_handle, err_handle = pending[name]
        entry = catalog["servers"][name]
        port = int(entry["port"])
        if ping_ready(port):
            server_status[name]["state"] = "started"
            print(f"OK ready 127.0.0.1:{port} ({name})")
            pending.pop(name)
        elif process is not None and process.poll() is not None:
            server_status[name]["state"] = "exited"
            server_status[name]["exit_code"] = process.returncode
            print(f"FAIL {name}: exited code={process.returncode}", file=sys.stderr)
            pending.pop(name)
            failed += 1
        elif process is None:
            pid = read_pid(pid_dir / f"{name}.pid")
            if pid is None:
                server_status[name]["state"] = "stale_pid"
                print(f"FAIL {name}: managed PID disappeared", file=sys.stderr)
                pending.pop(name)
                failed += 1
        if name in pending and now >= deadline:
            server_status[name]["state"] = "readiness_timeout"
            print(f"FAIL {name}: readiness timeout", file=sys.stderr)
            if process is not None:
                stop_group(process)
            pending.pop(name)
            failed += 1
        if name not in pending:
            if out_handle is not None:
                out_handle.close()
            if err_handle is not None:
                err_handle.close()
    if pending:
        time.sleep(0.5)

if mode == "daily" and not selected:
    selected_names = {name for name, _ in items}
    for name, entry in catalog["servers"].items():
        if name not in selected_names:
            server_status[name] = {
                "port": int(entry["port"]),
                "state": "skipped_optional",
                "url": f"http://127.0.0.1:{int(entry['port'])}{entry.get('path') or '/mcp'}",
            }

status["failed"] = failed
status_path = log_dir / "status.json"
atomic_text(status_path, json.dumps(status, indent=2, sort_keys=True) + "\n")
print(f"Wrote {status_path} failed={failed}")
raise SystemExit(1 if failed else 0)
PY
