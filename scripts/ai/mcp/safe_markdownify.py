"""Independent, read-only Markdownify owner with handle-checked local inputs.

The original D:/pc-agent Markdownify service is never modified or stopped.
No URL, git repository, arbitrary command or original-path converter is exposed.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import importlib.util
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
HOST = Path("D:/pc-agent/tools/shared-mcp")
PYTHON = Path("C:/Users/Fedor/AppData/Local/Programs/Python/Python313/python.exe")
SITE = "D:/github/BioactivityDataAcquisition/.venv-win/Lib/site-packages"


TRANSITION_LOCK = "transition.lock"
STATUS_RECORD = "status.json"
STOP_REQUEST = "stop.request"
HEALTH_PATH = "/health"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
SESSION_LIMIT = 64
SESSION_IDLE_SECONDS = 15 * 60


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


files = module("markdownify_safe_file", HERE / "safe_file.py")
snapshots = module("markdownify_converter_snapshot", HERE / "converter_snapshot.py")
core = scope = roots = runtime = psutil = None


def bootstrap_host():
    global core, scope, roots, runtime, psutil
    if core is not None:
        return
    if os.name != "nt":
        raise OSError("This scoped file owner requires Windows")
    sys.path.append(SITE)
    psutil = __import__("psutil")
    core = module("markdownify_primitives", HOST / "supervisor.py")
    scope = module("markdownify_scope", HOST / "project-memory-scope.py")
    roots = module("markdownify_roots", HOST / "ast-workspace-profile.py")
    runtime = module(
        "markdownify_runtime_dependencies", HOST / "project-memory-runtime.py"
    )


EXTENSIONS = {
    "pdf-to-markdown": ".pdf",
    "docx-to-markdown": ".docx",
    "pptx-to-markdown": ".pptx",
    "xlsx-to-markdown": ".xlsx",
    "html-to-markdown": ".html",
    "get-markdown-file": ".md",
}
TOOLS = [
    {
        "name": name,
        "description": "Read or convert a handle-verified project file",
        "inputSchema": {
            "type": "object",
            "properties": {"filepath": {"type": "string"}},
            "required": ["filepath"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    }
    for name in EXTENSIONS
]


def identity(root):
    bootstrap_host()
    root = roots.physical_root(root)
    value = {
        "schema": 1,
        "root": str(root),
        "account": scope.account_sid(),
        "device": root.stat().st_dev,
        "inode": root.stat().st_ino,
        "git_common": str(roots.CANONICAL / ".git"),
    }
    return hashlib.sha256(scope.canonical(value)).hexdigest(), value


def configure(root):
    key, binding = identity(root)
    core.STATE = (
        Path.home() / "AppData/Local/pc-agent/mcp-shared/markdownify-bioetl-v1" / key
    )
    scope.physical(core.STATE, exists=False)
    return key, binding


def pins(converter):
    paths = [
        HERE / "safe_markdownify.py",
        HERE / "safe_file.py",
        HOST / "supervisor.py",
        HERE / "converter_snapshot.py",
        HERE / "converter_runner.py",
        HOST / "project-memory-runtime.py",
        HOST / "project-memory-scope.py",
        HOST / "ast-workspace-profile.py",
        PYTHON,
        Path(converter) / "converter.json",
    ]
    snapshots.verify(Path(converter))
    result = {str(path): core.sha(path) for path in paths}
    result.update(runtime.python_hashes())
    return result


def specification(root):
    key, binding = configure(root)
    spec = core.read_json(core.STATE / "profile.json")
    if (
        spec["id"] != key
        or spec["binding"] != binding
        or spec["pins"] != pins(spec["converter"])
    ):
        raise PermissionError("Markdownify profile/runtime drift")
    return spec


def prepare(root):
    key, binding = configure(root)
    core.private_directory()
    with core.LifetimeLock(core.STATE / TRANSITION_LOCK):
        path = core.STATE / "profile.json"
        if path.exists():
            return specification(root)
        if any(core.STATE.iterdir()):
            if any(p.name != TRANSITION_LOCK for p in core.STATE.iterdir()):
                raise PermissionError("Incomplete Markdownify profile; no overwrite")
        site = PYTHON.parent / "Lib/site-packages"
        qualified = set()
        for extension in ("docx", "pdf", "pptx", "xlsx"):
            try:
                snapshots.closure(site, qualified | {extension})
                qualified.add(extension)
            except (KeyError, ValueError):
                pass  # Unavailable formats remain unadvertised and disabled.
        converter = snapshots.build(
            Path("D:/pc-agent/tools/markdownify-converter-versions"), site, qualified
        )
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        enabled = [
            name
            for name, suffix in EXTENSIONS.items()
            if suffix in {".md", ".html", *("." + x for x in qualified)}
        ]
        spec = {
            "id": key,
            "binding": binding,
            "port": port,
            "converter": str(converter),
            "enabled_tools": enabled,
            "pins": pins(converter),
        }
        core.credential(create=True)
        core.write_json(path, spec)
        return spec


def request(spec, method, path, body=None, session=None):
    record = core.read_json(core.STATE / STATUS_RECORD)
    if core.process_birth(record["owner_pid"]) != record["owner_birth"]:
        raise PermissionError("Markdownify owner identity unavailable")
    connection = http.client.HTTPConnection("127.0.0.1", spec["port"], timeout=100)
    connection.connect()
    local_port = connection.sock.getsockname()[1]
    matched = [
        row
        for row in psutil.net_connections(kind="tcp")
        if row.status == "ESTABLISHED"
        and row.laddr.ip == "127.0.0.1"
        and row.laddr.port == spec["port"]
        and row.raddr
        and row.raddr.port == local_port
    ]
    if not matched or any(row.pid != record["owner_pid"] for row in matched):
        connection.close()
        raise PermissionError("Markdownify socket identity unavailable")
    headers = {
        "Authorization": "Bearer " + core.credential(),
        "Content-Type": "application/json",
    }
    if session:
        headers["Mcp-Session-Id"] = session
    try:
        connection.request(
            method, path, json.dumps(body) if body is not None else None, headers
        )
        response = connection.getresponse()
        data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES or response.status >= 400:
            raise PermissionError("Markdownify request refused; no replay")
        return (json.loads(data) if data else None), response.getheader(
            "Mcp-Session-Id"
        )
    finally:
        connection.close()


def _optional_status_record():
    path = core.STATE / STATUS_RECORD
    return core.read_json(path) if path.exists() else {}


def _owner_ready(spec, record):
    try:
        health, _ = request(spec, "GET", HEALTH_PATH)
        return health["ready"] and health["generation"] == record["generation"]
    except (OSError, PermissionError):
        return False


def _launch_owner(root, record, launched):
    with core.LifetimeLock(core.STATE / TRANSITION_LOCK):
        current = _optional_status_record()
        if current != record:
            return False
        if launched:
            raise PermissionError("Markdownify exited during startup; no launch loop")
        child = subprocess.Popen(
            [
                str(PYTHON),
                "-I",
                "-S",
                "-B",
                str(HERE / "safe_markdownify.py"),
                "serve",
                f"--root={root}",
            ],
            cwd=HERE,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=core.WINDOWS_HIDE | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        birth = core.process_birth(child.pid)
        if birth is None:
            raise PermissionError("Markdownify launch identity unknown")
        core.write_json(
            core.STATE / STATUS_RECORD,
            {
                "owner_pid": child.pid,
                "owner_birth": birth,
                "generation": uuid.uuid4().hex,
            },
        )
        return True


def ensure(root):
    spec = specification(root)
    if (core.STATE / STOP_REQUEST).exists():
        raise PermissionError("Markdownify profile is administratively stopped")
    launched = False
    for _ in range(160):
        record = _optional_status_record()
        pid, birth = record.get("owner_pid"), record.get("owner_birth")
        if pid and core.process_birth(pid) == birth:
            if _owner_ready(spec, record):
                return spec
        elif pid and psutil.pid_exists(pid):
            raise PermissionError("Reused or unknown Markdownify PID")
        else:
            if not _launch_owner(root, record, launched):
                continue
            launched = True
        time.sleep(0.2)
    raise TimeoutError("Markdownify startup deadline; no fallback")


def convert(spec, name, args):
    if name not in spec["enabled_tools"] or set(args) != {"filepath"}:
        raise PermissionError("Unsupported Markdownify tool or arguments")
    source = args["filepath"]
    if not isinstance(source, str) or Path(source).suffix.lower() != EXTENSIONS[name]:
        raise PermissionError("Unsupported conversion file type")
    raw = files.read_confined(Path(spec["binding"]["root"]), source)
    if name == "get-markdown-file":
        return raw.decode("utf-8-sig")
    job = core.STATE / ("job-" + uuid.uuid4().hex)
    job.mkdir(mode=0o700)
    snapshot = job / ("input" + EXTENSIONS[name])
    snapshot.write_bytes(raw)
    output_path = job / "output.md"
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper()
        in {
            "SYSTEMROOT",
            "WINDIR",
            "PATH",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "TEMP",
            "TMP",
            "PATHEXT",
        }
    }
    env["PYTHONUTF8"] = "1"
    owned = core.Job()
    child = None
    try:
        with output_path.open("xb") as output_stream:
            child = subprocess.Popen(
                [
                    str(PYTHON),
                    "-I",
                    "-S",
                    "-B",
                    str(Path(spec["converter"]) / "converter_runner.py"),
                    str(snapshot),
                ],
                cwd=job,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=output_stream,
                stderr=subprocess.DEVNULL,
                creationflags=core.WINDOWS_HIDE,
            )
            owned.attach(child)
            child.wait(timeout=90)
        with output_path.open("rb") as output_stream:
            output = output_stream.read(1024 * 1024 + 1)
        if child.returncode or len(output) > 1024 * 1024:
            raise ValueError("Conversion failed or exceeded output bound")
        return output.decode("utf-8")
    finally:
        owned.close()
        if child and child.poll() is None:
            child.wait(timeout=10)
        snapshot.unlink()
        output_path.unlink(missing_ok=True)
        job.rmdir()


class _SessionRegistry:
    """Bound concurrent sessions and reclaim disconnected clients after inactivity."""

    def __init__(self, *, clock=time.monotonic):
        self._clock = clock
        self._seen = {}
        self._lock = threading.Lock()

    def _expire(self, now):
        expired = [
            key
            for key, seen in self._seen.items()
            if now - seen >= SESSION_IDLE_SECONDS
        ]
        for key in expired:
            del self._seen[key]

    def issue(self):
        with self._lock:
            now = self._clock()
            self._expire(now)
            if len(self._seen) >= SESSION_LIMIT:
                return None
            session = uuid.uuid4().hex
            self._seen[session] = now
            return session

    def touch(self, session):
        with self._lock:
            now = self._clock()
            self._expire(now)
            if session not in self._seen:
                return False
            self._seen[session] = now
            return True

    def discard(self, session):
        with self._lock:
            self._seen.pop(session, None)


def _response_bytes(value):
    if value is None:
        return b""
    # JSON permits escaped unpaired surrogates in request identifiers. Preserve
    # those escapes while keeping ordinary Unicode text in compact UTF-8.
    raw = json.dumps(value, ensure_ascii=False).encode(
        "utf-8", errors="backslashreplace"
    )
    if len(raw) <= MAX_RESPONSE_BYTES:
        return raw
    error = {
        "jsonrpc": "2.0",
        "id": value.get("id") if isinstance(value, dict) else None,
        "result": {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": "Local conversion response exceeds transport bound",
                }
            ],
        },
    }
    raw = json.dumps(error, ensure_ascii=False).encode(
        "utf-8", errors="backslashreplace"
    )
    if len(raw) > MAX_RESPONSE_BYTES:
        # An oversized request identifier must not defeat the envelope bound.
        error["id"] = None
        raw = json.dumps(error, ensure_ascii=False).encode(
            "utf-8", errors="backslashreplace"
        )
    return raw


class _MarkdownifyHandler(BaseHTTPRequestHandler):
    def __init__(
        self, *args, workspace, spec, record, token, sessions, gate, draining, **kwargs
    ):
        self._workspace = workspace
        self._spec = spec
        self._record = record
        self._token = token
        self._sessions = sessions
        self._gate = gate
        self._draining = draining
        super().__init__(*args, **kwargs)

    def log_message(self, *_):
        # Requests contain credentials and paths; never emit access logs.
        pass

    def reply(self, status, value=None, session=None):
        raw = _response_bytes(value)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        if session:
            self.send_header("Mcp-Session-Id", session)
        self.end_headers()
        self.wfile.write(raw)

    def authorized(self):
        if not secrets.compare_digest(
            self.headers.get("Authorization", ""), "Bearer " + self._token
        ):
            self.reply(401)
            return False
        specification(self._workspace)
        return True

    def do_GET(self):
        if not self.authorized():
            return
        if self.path == HEALTH_PATH:
            self.reply(
                200,
                {
                    "ready": True,
                    "service": "markdownify-bioetl",
                    "generation": self._record["generation"],
                },
            )
        else:
            self.reply(405)

    def do_DELETE(self):
        if self.authorized():
            self._sessions.discard(self.headers.get("Mcp-Session-Id"))
            self.reply(200)

    def do_POST(self):
        if not self.authorized():
            return
        if self.path != "/mcp":
            self.reply(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 1024 * 1024:
            self.reply(413)
            return
        request_value = json.loads(self.rfile.read(length))
        self._dispatch_request(request_value)

    def _dispatch_request(self, request_value):
        identifier = request_value.get("id")
        method = request_value.get("method")
        session = self.headers.get("Mcp-Session-Id")
        if method == "initialize":
            session = None if self._draining.is_set() else self._sessions.issue()
            if session is None:
                self.reply(503)
                return
            result = {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "markdownify-bioetl",
                    "version": "1.0.0",
                },
            }
        elif not self._sessions.touch(session):
            self.reply(404)
            return
        elif identifier is None:
            self.reply(202)
            return
        elif method == "tools/list":
            result = {
                "tools": [
                    tool
                    for tool in TOOLS
                    if tool["name"] in self._spec["enabled_tools"]
                ]
            }
        elif method == "ping":
            result = {}
        elif method == "tools/call":
            result = self._call_tool(request_value)
        else:
            self.reply(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": identifier,
                    "error": {"code": -32601, "message": "Unsupported method"},
                },
            )
            return
        self.reply(200, {"jsonrpc": "2.0", "id": identifier, "result": result}, session)

    def _call_tool(self, request_value):
        with self._gate:
            try:
                if self._draining.is_set():
                    raise PermissionError("Markdownify is draining")
                params = request_value["params"]
                text = convert(self._spec, params["name"], params.get("arguments", {}))
                result = {"content": [{"type": "text", "text": text}]}
            except Exception:
                result = {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": "Local file access/conversion refused",
                        }
                    ],
                }
        return result


def serve(root):
    spec = specification(root)
    with core.LifetimeLock(core.STATE / "owner.lock"):
        # Parent publishes PID+birth before this process binds the port.
        for _ in range(100):
            if (core.STATE / STATUS_RECORD).is_file():
                record = core.read_json(core.STATE / STATUS_RECORD)
                if record.get("owner_pid") == os.getpid() and record.get(
                    "owner_birth"
                ) == core.process_birth(os.getpid()):
                    break
            time.sleep(0.05)
        else:
            raise PermissionError("Markdownify launch was not published")
        token = core.credential()
        sessions = _SessionRegistry()
        gate = threading.Lock()
        draining = threading.Event()

        handler = partial(
            _MarkdownifyHandler,
            workspace=root,
            spec=spec,
            record=record,
            token=token,
            sessions=sessions,
            gate=gate,
            draining=draining,
        )
        server = ThreadingHTTPServer(
            ("127.0.0.1", spec["port"]), handler, bind_and_activate=False
        )
        server.allow_reuse_address = False
        server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        server.server_bind()
        server.server_activate()
        server.daemon_threads = True

        def stop_when_requested():
            marker = core.STATE / STOP_REQUEST
            while not marker.exists():
                time.sleep(0.2)
            if core.read_json(marker).get("generation") != record["generation"]:
                return
            draining.set()
            with gate:
                server.shutdown()

        threading.Thread(target=stop_when_requested, daemon=True).start()
        server.serve_forever(poll_interval=0.2)
        server.server_close()


def client(root):
    spec = specification(root)
    health, _ = request(spec, "GET", HEALTH_PATH)
    if not health.get("ready"):
        raise PermissionError(
            "Markdownify owner requires explicit administrative start"
        )
    session = None
    try:
        for line in sys.stdin:
            if len(line) > 1024 * 1024:
                raise ValueError("Oversized Markdownify request")
            value = json.loads(line)
            result, next_session = request(spec, "POST", "/mcp", value, session)
            session = next_session or session
            if result is not None:
                print(json.dumps(result), flush=True)
    finally:
        if session:
            request(spec, "DELETE", "/mcp", session=session)


def _start(root):
    value = specification(root)
    marker = core.STATE / STOP_REQUEST
    if marker.exists():
        record = core.read_json(core.STATE / STATUS_RECORD)
        if (
            psutil.pid_exists(record["owner_pid"])
            or core.read_json(marker).get("generation") != record["generation"]
        ):
            raise PermissionError("Markdownify stop has not completed")
        marker.unlink()
    ensure(root)
    print(json.dumps({"ready": True, "id": value["id"]}))


def _stop(root):
    specification(root)
    record = core.read_json(core.STATE / STATUS_RECORD)
    if core.process_birth(record["owner_pid"]) != record["owner_birth"]:
        raise PermissionError("Markdownify owner identity not proven")
    core.write_json(core.STATE / STOP_REQUEST, {"generation": record["generation"]})
    for _ in range(200):
        if not psutil.pid_exists(record["owner_pid"]):
            print(json.dumps({"state": "STOPPED"}))
            return
        time.sleep(0.2)
    print(json.dumps({"state": "DRAIN_PENDING"}))


def _client_root(args):
    if args.root is not None:
        raise PermissionError("Client root override is forbidden")
    root = next(
        (p for p in (Path.cwd(), *Path.cwd().parents) if (p / ".git").exists()),
        None,
    )
    if root is None:
        raise PermissionError("No session workspace")
    roots.physical_root(root)
    return root


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("prepare", "serve", "status", "client", "start", "stop")
    )
    parser.add_argument("--root", type=Path)
    args = parser.parse_args(argv)
    bootstrap_host()
    if args.mode == "client":
        root = _client_root(args)
        client(root)
    elif args.root is None:
        raise ValueError("Administrative root required")
    elif args.mode == "prepare":
        value = prepare(args.root)
        print(json.dumps({"prepared": True, "id": value["id"], "port": value["port"]}))
    elif args.mode == "serve":
        serve(args.root)
    elif args.mode == "start":
        _start(root=args.root)
    elif args.mode == "stop":
        _stop(root=args.root)
    else:
        value = specification(args.root)
        print(json.dumps(request(value, "GET", HEALTH_PATH)[0]))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.stderr.write(
            "Safe Markdownify operation refused; no credential or fallback exposed.\n"
        )
        raise SystemExit(64) from None
