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
import math
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from contextlib import contextmanager
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
RETIRED_GENERATION = "retired_generation"
HEALTH_PATH = "/health"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
SESSION_LIMIT = 64
SESSION_IDLE_SECONDS = 15 * 60
HTTP_CONNECTION_LIMIT = 64
HTTP_READ_SECONDS = 5
STARTUP_SECONDS = 32
PENDING_CLEANUP = "cleanup.pending.json"
WORKER_OUTPUT = "output.md"
WORKER_SECONDS = 70
WORKER_CLEANUP_SECONDS = 5
WORKER_NONCE_ENV = "PC_AGENT_MARKDOWNIFY_LAUNCH_NONCE"
OWNER_IDENTITY_ERROR = "Markdownify owner identity is unknown"


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


def _control_pins():
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
    ]
    result = {str(path): core.sha(path) for path in paths}
    result.update(runtime.python_hashes())
    return result


def pins(converter):
    snapshots.verify(Path(converter))
    result = _control_pins()
    path = Path(converter) / "converter.json"
    result[str(path)] = core.sha(path)
    return result


def specification(root, *, for_stop=False):
    key, binding = configure(root)
    spec = core.read_json(core.STATE / "profile.json")
    if spec.get("schema") != 2 or spec["id"] != key or spec["binding"] != binding:
        raise PermissionError("Markdownify profile/runtime drift")
    if not for_stop and (
        pins(spec["converter"]) != spec["pins"] or not _qualification_matches(spec)
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
        _retry_pending_jobs()
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
        spec = {
            "schema": 2,
            "id": key,
            "binding": binding,
            "converter": str(converter),
            "pins": pins(converter),
        }
        spec["qualification"] = _qualify_converter(spec, qualified)
        _retry_pending_jobs()
        spec["enabled_tools"] = _enabled_tools(spec["qualification"])
        core.credential(create=True)
        core.write_json(path, spec)
        return spec


def _enabled_tools(qualification):
    return [name for name in EXTENSIONS if qualification["results"].get(name) == "PASS"]


def _qualification_matches(spec):
    evidence = spec.get("qualification", {})
    results = evidence.get("results", {})
    return (
        evidence.get("schema") == 1
        and evidence.get("converter") == Path(spec["converter"]).name
        and set(results) == set(EXTENSIONS)
        and all(value in {"PASS", "FAIL", "UNAVAILABLE"} for value in results.values())
        and spec["enabled_tools"] == _enabled_tools(evidence)
    )


def _qualify_converter(spec, available):
    results = dict.fromkeys(EXTENSIONS, "UNAVAILABLE")
    results["get-markdown-file"] = "PASS"
    candidates = {".html", *("." + name for name in available)}
    for name, extension in EXTENSIONS.items():
        if extension not in candidates:
            continue
        try:
            output = _convert_bytes(
                spec, extension, snapshots.qualification_sample(extension)
            )
            results[name] = "PASS" if snapshots.QUALIFICATION_TEXT in output else "FAIL"
        except (OSError, ValueError, subprocess.SubprocessError):
            results[name] = "FAIL"
    return {"schema": 1, "converter": Path(spec["converter"]).name, "results": results}


class _SessionExpired(PermissionError):
    """A session-scoped 404 requires a fresh handshake, never replay."""


def _response_value(response, method, path, session):
    data = response.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise PermissionError("Markdownify response exceeds transport bound")
    if response.status == 404 and session and method == "POST" and path == "/mcp":
        raise _SessionExpired("Markdownify session expired; no replay")
    if response.status >= 400:
        raise PermissionError("Markdownify request refused; no replay")
    return (json.loads(data) if data else None), response.getheader("Mcp-Session-Id")


def _expire_socket(sock):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass


@contextmanager
def _bounded_connection(connection, timeout):
    deadline = time.monotonic() + timeout
    timer = None
    try:
        connection.connect()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Markdownify connection deadline expired")
        connection.sock.settimeout(remaining)
        timer = threading.Timer(remaining, _expire_socket, args=(connection.sock,))
        timer.daemon = True
        timer.start()
        yield
    finally:
        if timer is not None:
            timer.cancel()
        connection.close()


def _connection_record(spec):
    if spec.get("id") != core.STATE.name:
        raise PermissionError("Markdownify endpoint belongs to another profile")
    record = core.read_json(core.STATE / STATUS_RECORD) or {}
    pid, birth = _recorded_owner_identity(record)
    port = record.get("port")
    if not pid or type(port) is not int or not 0 < port < 65536:
        raise PermissionError("Markdownify owner endpoint is not published")
    if core.process_birth(pid) != birth:
        raise PermissionError("Markdownify owner identity unavailable")
    return record


def _verify_connection_peer(connection, record):
    local_port = connection.sock.getsockname()[1]
    matched = [
        row
        for row in psutil.net_connections(kind="tcp")
        if row.status == "ESTABLISHED"
        and row.laddr.ip == "127.0.0.1"
        and row.laddr.port == record["port"]
        and row.raddr
        and row.raddr.port == local_port
    ]
    if (
        not matched
        or any(row.pid != record["owner_pid"] for row in matched)
        or core.process_birth(record["owner_pid"]) != record["owner_birth"]
    ):
        raise PermissionError("Markdownify socket identity unavailable")


def request(spec, method, path, body=None, session=None, *, timeout=100):
    payload = (
        None
        if body is None
        else json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8", errors="backslashreplace"
        )
    )
    if payload is not None and len(payload) > 1024 * 1024:
        raise ValueError("Oversized Markdownify request")
    if timeout <= 0:
        raise TimeoutError("Markdownify request deadline expired")
    record = _connection_record(spec)
    connection = http.client.HTTPConnection(
        "127.0.0.1", record["port"], timeout=timeout
    )
    connection.auto_open = False
    with _bounded_connection(connection, timeout):
        _verify_connection_peer(connection, record)
        headers = {
            "Authorization": "Bearer " + core.credential(),
            "Content-Type": "application/json",
        }
        if session:
            headers["Mcp-Session-Id"] = session
        connection.request(method, path, payload, headers)
        return _response_value(connection.getresponse(), method, path, session)


def _optional_status_record():
    path = core.STATE / STATUS_RECORD
    return core.read_json(path) if path.exists() else {}


def _owner_ready(spec, record, *, timeout=100):
    try:
        health, _ = request(spec, "GET", HEALTH_PATH, timeout=timeout)
        return health["ready"] and health["generation"] == record["generation"]
    except (OSError, PermissionError, http.client.HTTPException):
        return False


def _launch_owner(root, record, launched):
    with core.LifetimeLock(core.STATE / TRANSITION_LOCK):
        current = _optional_status_record()
        if (core.STATE / STOP_REQUEST).exists():
            raise PermissionError("Markdownify profile is administratively stopped")
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


def _recorded_owner_identity(record):
    pid, birth = record.get("owner_pid"), record.get("owner_birth")
    if record and not pid and set(record) != {RETIRED_GENERATION}:
        raise PermissionError(OWNER_IDENTITY_ERROR)
    if pid is not None and (
        type(pid) is not int
        or pid <= 0
        or type(birth) not in {int, float}
        or not math.isfinite(birth)
    ):
        raise PermissionError(OWNER_IDENTITY_ERROR)
    return pid, birth


def _startup_step(root, spec, record, launched, deadline):
    pid, birth = _recorded_owner_identity(record)
    if pid and core.process_birth(pid) == birth:
        ready = _owner_ready(spec, record, timeout=deadline - time.monotonic())
        return ready, launched
    if pid and psutil.pid_exists(pid):
        raise PermissionError("Reused or unknown Markdownify PID")
    if time.monotonic() >= deadline:
        raise TimeoutError("Markdownify startup deadline; no fallback")
    return False, _launch_owner(root, record, launched) or launched


def ensure(root):
    deadline = time.monotonic() + STARTUP_SECONDS
    spec = specification(root)
    if (core.STATE / STOP_REQUEST).exists():
        raise PermissionError("Markdownify profile is administratively stopped")
    launched = False
    while time.monotonic() < deadline:
        ready, launched = _startup_step(
            root, spec, _optional_status_record(), launched, deadline
        )
        if ready and time.monotonic() < deadline:
            return spec
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(0.2, remaining))
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
    return _convert_bytes(spec, EXTENSIONS[name], raw)


def _worker_job_name(name):
    return (
        name.startswith("job-")
        and len(name) == 36
        and all(char in "0123456789abcdef" for char in name[4:])
    )


def _check_worker_job(job):
    if (
        job.parent != core.STATE
        or not _worker_job_name(job.name)
        or core.STATE.resolve(strict=True) != core.STATE
        or job.resolve(strict=True) != job
        or not job.is_dir()
    ):
        raise PermissionError("Worker cleanup namespace is not physical")
    for path in job.iterdir():
        if (
            path.is_symlink()
            or getattr(path, "is_junction", lambda: False)()
            or path.resolve(strict=True) != path
        ):
            raise PermissionError("Worker cleanup path changed")
        if path.is_file() and path.stat().st_nlink != 1:
            raise PermissionError("Worker cleanup file has an unowned link")


def _pending_worker_record_name(path):
    prefix, suffix = PENDING_CLEANUP + ".", ".pending"
    name = path.name
    if not name.startswith(prefix) or not name.endswith(suffix):
        return False
    identity = name[len(prefix) : -len(suffix)]
    return len(identity) == 32 and all(char in "0123456789abcdef" for char in identity)


def _erase_worker_job(job, snapshot):
    _validate_cleanup_files(job, snapshot)
    # Keep the recovery journal until every document/output/temp is gone.
    paths = sorted(job.iterdir(), key=lambda path: path.name == PENDING_CLEANUP)
    for path in paths:
        if path.name in {
            snapshot,
            WORKER_OUTPUT,
            PENDING_CLEANUP,
        } or _pending_worker_record_name(path):
            path.unlink()
    job.rmdir()


def _validate_cleanup_files(job, snapshot):
    _check_worker_job(job)
    permitted = {"input" + ext for ext in EXTENSIONS.values() if ext != ".md"}
    if snapshot not in permitted or any(
        path.name not in {snapshot, WORKER_OUTPUT, PENDING_CLEANUP}
        and not _pending_worker_record_name(path)
        for path in job.iterdir()
    ):
        raise PermissionError("Worker cleanup contains unowned files")


def _identity_finished(pid, birth):
    if (
        type(pid) is not int
        or pid <= 0
        or (
            birth is not None
            and (type(birth) not in {int, float} or not math.isfinite(birth))
        )
    ):
        raise PermissionError("Pending worker identity is unknown")
    current = core.process_birth(pid)
    if current is not None:
        return birth is not None and current != birth
    return not psutil.pid_exists(pid)


def _validate_worker_record(record, job):
    common = {"schema", "job", "snapshot", "worker_pid", "worker_birth", "job_closed"}
    if not isinstance(record, dict) or record.get("job") != job.name:
        raise PermissionError("Unsupported pending worker cleanup")
    schema = record.get("schema")
    fields = common if schema == 1 else common | {"owner_pid", "owner_birth", "phase"}
    if (
        type(schema) is not int
        or schema not in {1, 2}
        or set(record) != fields
        or type(record["job_closed"]) is not bool
    ):
        raise PermissionError("Unsupported pending worker cleanup")
    return schema


def _journal_phase_finished(record):
    owner_finished = _identity_finished(record["owner_pid"], record["owner_birth"])
    if record["phase"] in {"PREPARED", "SPAWNING"}:
        # EOF on the private launch pipe prevents an orphan from reading input.
        return owner_finished and record["worker_pid"] is record[
            "worker_birth"
        ] is None, owner_finished
    if record["phase"] not in {"RUNNING", "CLEANUP"}:
        raise PermissionError("Unsupported pending worker phase")
    if record["phase"] == "RUNNING" and (
        record["worker_pid"] is None or record["worker_birth"] is None
    ):
        raise PermissionError("Running worker identity is incomplete")
    return None, owner_finished


def _pending_worker_finished(record, job):
    schema = _validate_worker_record(record, job)
    owner_finished = False
    if schema == 2:
        finished, owner_finished = _journal_phase_finished(record)
        if finished is not None:
            return finished
    if record["job_closed"] is not True and not owner_finished:
        return False
    pid, birth = record["worker_pid"], record["worker_birth"]
    if pid is None:
        return birth is None and record["job_closed"] is True
    return _identity_finished(pid, birth)


def _discard_unpublished_control(job):
    pending = list(job.iterdir())
    if not all(_pending_worker_record_name(path) for path in pending):
        raise PermissionError("Previous worker cleanup has no identity record")
    for path in pending:
        path.unlink()
    job.rmdir()


def _retry_worker_job(job):
    _check_worker_job(job)
    marker = job / PENDING_CLEANUP
    if not marker.exists():
        _discard_unpublished_control(job)
        return
    record = core.read_json(marker)
    if not _pending_worker_finished(record, job):
        raise PermissionError("Previous worker cleanup remains pending")
    _validate_cleanup_files(job, record.get("snapshot"))
    try:
        _erase_worker_job(job, record.get("snapshot"))
    except OSError:
        _validate_cleanup_files(job, record.get("snapshot"))
        core.write_json(marker, record)
        raise


def _retry_pending_jobs():
    for job in core.STATE.iterdir():
        if _worker_job_name(job.name):
            _retry_worker_job(job)


def _close_worker(owned, child):
    closed, problem = owned is None, None
    try:
        if owned is not None:
            owned.close()
            closed = True
    except Exception as error:
        problem = error
    try:
        if child is not None:
            if child.poll() is None:
                child.terminate()  # Only the exact child handle created here.
            child.wait(timeout=WORKER_CLEANUP_SECONDS)
    except Exception as error:
        problem = problem or error
    if child is not None and child.stdin:
        try:
            child.stdin.close()
        except Exception as error:
            problem = problem or error
    return closed, problem


def _new_worker_record(job, snapshot):
    birth = core.process_birth(os.getpid())
    if type(birth) not in {int, float} or not math.isfinite(birth):
        raise PermissionError("Conversion owner identity is unknown")
    return {
        "schema": 2,
        "job": job.name,
        "snapshot": snapshot.name,
        "owner_pid": os.getpid(),
        "owner_birth": birth,
        "worker_pid": None,
        "worker_birth": None,
        "job_closed": False,
        "phase": "PREPARED",
    }


def _write_worker_record(job, record, phase):
    record["phase"] = phase
    core.write_json(job / PENDING_CLEANUP, record)


def _finish_worker(job, snapshot, owned, child, record):
    closed, problem = _close_worker(owned, child)
    if record is not None:
        record["job_closed"] = closed
    if problem is not None:
        if record is not None:
            _write_worker_record(job, record, "CLEANUP")
        raise problem
    try:
        _erase_worker_job(job, snapshot.name)
    except OSError:
        if record is not None:
            _write_worker_record(job, record, "CLEANUP")
        raise


def _convert_bytes(spec, extension, raw):
    """Execute a pinned worker on an owner-private snapshot, including probes."""
    deadline = time.monotonic() + WORKER_SECONDS
    _retry_pending_jobs()
    job = core.STATE / ("job-" + uuid.uuid4().hex)
    job.mkdir(mode=0o700)
    snapshot = job / ("input" + extension)
    output_path = job / WORKER_OUTPUT
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
    nonce = secrets.token_hex(32)
    env[WORKER_NONCE_ENV] = nonce
    owned = None
    child = None
    record = None
    failed = True
    try:
        record = _new_worker_record(job, snapshot)
        _write_worker_record(job, record, "PREPARED")
        snapshot.write_bytes(raw)
        owned = core.Job()
        with output_path.open("xb") as output_stream:
            _write_worker_record(job, record, "SPAWNING")
            if time.monotonic() >= deadline:
                raise TimeoutError("Conversion execution deadline")
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
                stdin=subprocess.PIPE,
                stdout=output_stream,
                stderr=subprocess.DEVNULL,
                creationflags=core.WINDOWS_HIDE,
            )
            record["worker_pid"] = child.pid
            record["worker_birth"] = core.process_birth(child.pid)
            owned.attach(child)
            if record["worker_birth"] is None:
                raise PermissionError("Conversion worker identity is unknown")
            _write_worker_record(job, record, "RUNNING")
            child.stdin.write((nonce + "\n").encode())
            child.stdin.flush()
            child.wait(timeout=max(0, deadline - time.monotonic()))
        with output_path.open("rb") as output_stream:
            output = output_stream.read(1024 * 1024 + 1)
        if child.returncode or len(output) > 1024 * 1024:
            raise ValueError("Conversion failed or exceeded output bound")
        text = output.decode("utf-8")
        failed = False
        return text
    finally:
        try:
            _finish_worker(job, snapshot, owned, child, record)
        except Exception:
            if not failed:
                raise


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


class _BoundedHTTPServer(ThreadingHTTPServer):
    """Limit unauthenticated connections and total header/body read time."""

    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, *args, **kwargs):
        self._slots = threading.BoundedSemaphore(HTTP_CONNECTION_LIMIT)
        self._deadlines = {}
        self._expired_readers = set()
        self._deadline_lock = threading.Lock()
        super().__init__(*args, **kwargs)

    def process_request(self, request_socket, client_address):
        if not self._slots.acquire(blocking=False):
            self.shutdown_request(request_socket)
            return
        try:
            request_socket.settimeout(HTTP_READ_SECONDS)
            super().process_request(request_socket, client_address)
        except BaseException:
            self._slots.release()
            self.shutdown_request(request_socket)
            raise

    def _expire_reader(self, request_socket):
        with self._deadline_lock:
            if request_socket not in self._deadlines:
                return
            self._expired_readers.add(request_socket)
            try:
                request_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                return  # The same owned connection has already closed.

    def finish_reading(self, request_socket, *, completed=False):
        with self._deadline_lock:
            timer = self._deadlines.pop(request_socket, None)
            expired = request_socket in self._expired_readers
            self._expired_readers.discard(request_socket)
            if timer is not None:
                timer.cancel()
        if completed and expired:
            raise TimeoutError("HTTP read deadline expired before dispatch")

    def process_request_thread(self, request_socket, client_address):
        delegated = False
        try:
            timer = threading.Timer(
                HTTP_READ_SECONDS, self._expire_reader, (request_socket,)
            )
            timer.daemon = True
            with self._deadline_lock:
                self._deadlines[request_socket] = timer
            timer.start()
            delegated = True
            super().process_request_thread(request_socket, client_address)
        finally:
            self.finish_reading(request_socket)
            if not delegated:
                self.shutdown_request(request_socket)
            self._slots.release()

    def handle_error(self, _request_socket, _client_address):
        # Authentication failures, disconnects and read deadlines expose no paths.
        return None


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
        if session is not None and not re.fullmatch(r"[0-9a-f]{32}", session):
            raise ValueError("Invalid session identifier")
        raw = _response_bytes(value)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        if session:
            self.send_header("Mcp-Session-Id", session)
        self.end_headers()
        self.wfile.write(raw)

    def authorized(self, *, verify_runtime=True):
        if not secrets.compare_digest(
            self.headers.get("Authorization", ""), "Bearer " + self._token
        ):
            self.reply(401)
            return False
        if verify_runtime:
            self._finish_reading()
            specification(self._workspace)
        return True

    def _finish_reading(self):
        server = getattr(self, "server", None)
        if isinstance(server, _BoundedHTTPServer):
            server.finish_reading(self.connection, completed=True)

    def do_GET(self):
        if not self.authorized():
            return
        self._finish_reading()
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
            self._finish_reading()
            self._sessions.discard(self.headers.get("Mcp-Session-Id"))
            self.reply(200)

    def do_POST(self):
        if not self.authorized(verify_runtime=False):
            return
        if self.path != "/mcp":
            self.reply(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1024 * 1024:
                self.reply(413)
                return
            raw = self.rfile.read(length)
            if len(raw) != length:
                self.close_connection = True
                raise ValueError("Incomplete request body")
            request_value = json.loads(raw)
            if not isinstance(request_value, dict):
                raise ValueError("Object required")
        except (OSError, ValueError):
            self.reply(400)
            return
        self._finish_reading()
        specification(self._workspace)
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
            self._call_tool(
                request_value,
                respond=lambda result: self.reply(
                    200, {"jsonrpc": "2.0", "id": identifier, "result": result}, session
                ),
            )
            return
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

    def _call_tool(self, request_value, *, respond=None):
        if not self._gate.acquire(blocking=False):
            result = {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": "Markdownify is busy; request not queued or executed",
                    }
                ],
            }
            if respond is not None:
                respond(result)
            return result
        try:
            result = self._conversion_result(request_value)
            if respond is not None:
                respond(result)
            return result
        finally:
            self._gate.release()

    def _conversion_result(self, request_value):
        try:
            if self._draining.is_set():
                raise PermissionError("Markdownify is draining")
            params = request_value["params"]
            text = convert(self._spec, params["name"], params.get("arguments", {}))
            return {"content": [{"type": "text", "text": text}]}
        except Exception:
            return {
                "isError": True,
                "content": [
                    {"type": "text", "text": "Local file access/conversion refused"}
                ],
            }


def _watch_stop(server, record, gate, draining):
    marker = core.STATE / STOP_REQUEST
    while True:
        try:
            requested = core.read_json(marker)
        except FileNotFoundError:
            requested = {}
        if requested.get("generation") == record["generation"]:
            draining.set()
            with gate:
                server.shutdown()
            return
        time.sleep(0.2)


def _publish_listener(server, record):
    with core.LifetimeLock(core.STATE / TRANSITION_LOCK):
        if (
            core.read_json(core.STATE / STATUS_RECORD) != record
            or (core.STATE / STOP_REQUEST).exists()
        ):
            raise PermissionError(
                "Markdownify launch changed before endpoint publication"
            )
        record["port"] = server.server_address[1]
        core.write_json(core.STATE / STATUS_RECORD, record)


def _bind_owner_server(handler):
    server = _BoundedHTTPServer(("127.0.0.1", 0), handler, bind_and_activate=False)
    server.allow_reuse_address = False
    try:
        exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
        if exclusive is not None:
            server.socket.setsockopt(socket.SOL_SOCKET, exclusive, 1)
        server.server_bind()
        server.server_activate()
        return server
    except BaseException:
        server.server_close()
        raise


def serve(root):
    spec = specification(root)
    _retry_pending_jobs()
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
        server = _bind_owner_server(handler)
        try:
            _publish_listener(server, record)
            server.daemon_threads = True
            threading.Thread(
                target=_watch_stop, args=(server, record, gate, draining), daemon=True
            ).start()
            server.serve_forever(poll_interval=0.2)
        finally:
            server.server_close()


def _renew_session(spec, initialization):
    if initialization is None:
        raise PermissionError("Expired session has no verified initialization")
    handshake = dict(initialization)
    response, session = request(spec, "POST", "/mcp", handshake)
    if not session or not isinstance(response, dict) or "result" not in response:
        raise PermissionError("Markdownify reinitialization refused")
    try:
        request(
            spec,
            "POST",
            "/mcp",
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            session,
        )
    except BaseException:
        _discard_session(spec, session)
        raise
    return session


def _discard_session(spec, session):
    try:
        request(spec, "DELETE", "/mcp", session=session)
    except Exception:
        pass  # Best effort; preserve the original operation failure.


def _forward_request(spec, value, session, initialization):
    try:
        response, next_session = request(spec, "POST", "/mcp", value, session)
        return response, next_session or session
    except _SessionExpired:
        if initialization is None:
            raise
        replacement = _renew_session(spec, initialization)
        response = (
            None
            if "id" not in value
            else {
                "jsonrpc": "2.0",
                "id": value["id"],
                "error": {
                    "code": -32000,
                    "message": "Session renewed; original request was not replayed or executed",
                },
            }
        )
        return response, replacement


def _stdio_requests(stream):
    # -I ignores PYTHONUTF8; redirected Windows stdin may otherwise use CP1251.
    binary = getattr(stream, "buffer", stream)
    limit = 1024 * 1024
    while True:
        raw = binary.readline(limit + 1)
        if not raw:
            return
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        if len(raw) > limit:
            raise ValueError("Oversized Markdownify request")
        yield json.loads(raw.decode("utf-8"))


def client(root):
    spec = specification(root)
    health, _ = request(spec, "GET", HEALTH_PATH)
    if not health.get("ready"):
        raise PermissionError(
            "Markdownify owner requires explicit administrative start"
        )
    session = None
    initialization = None
    try:
        for value in _stdio_requests(sys.stdin):
            result, session = _forward_request(spec, value, session, initialization)
            if value.get("method") == "initialize" and result and "result" in result:
                initialization = value
            if result is not None:
                print(json.dumps(result), flush=True)
    finally:
        if session:
            _discard_session(spec, session)


def _retire_stopped_record(record, marker_value):
    generation = marker_value["generation"]
    if not isinstance(generation, str) or uuid.UUID(generation).hex != generation:
        raise PermissionError("Invalid stopped generation")
    history = core.STATE / "restart-history"
    scope.physical(history, exists=False)
    archive = history / (generation + ".json")
    if set(record) == {RETIRED_GENERATION} and record[RETIRED_GENERATION] == generation:
        record = core.read_json(archive)["status"]
    if record.get("generation") != generation:
        raise PermissionError("Markdownify stopped generation changed")
    if (
        type(record.get("owner_pid")) is not int
        or record["owner_pid"] <= 0
        or type(record.get("owner_birth")) not in {int, float}
    ):
        raise PermissionError("Invalid stopped owner identity")
    actual = core.process_birth(record["owner_pid"])
    if actual == record["owner_birth"] or (
        actual is None and psutil.pid_exists(record["owner_pid"])
    ):
        raise PermissionError(
            "Markdownify stop has not completed or identity is unknown"
        )
    history.mkdir(exist_ok=True)
    evidence = {"status": record, "stop": marker_value}
    if archive.exists() and core.read_json(archive) != evidence:
        raise PermissionError("Markdownify restart history changed")
    if not archive.exists():
        core.write_json(archive, evidence)
    core.write_json(core.STATE / STATUS_RECORD, {RETIRED_GENERATION: generation})


def _retire_crashed_record(record):
    pid, birth = _recorded_owner_identity(record)
    if pid is None:
        return
    actual = core.process_birth(pid)
    if actual == birth:
        return
    if actual is None and psutil.pid_exists(pid):
        raise PermissionError(OWNER_IDENTITY_ERROR)
    generation = record.get("generation")
    if not isinstance(generation, str) or uuid.UUID(generation).hex != generation:
        raise PermissionError("Invalid crashed generation")
    if _optional_status_record() != record:
        raise PermissionError("Markdownify crashed generation changed")
    history = core.STATE / "restart-history"
    scope.physical(history, exists=False)
    history.mkdir(exist_ok=True)
    archive = history / (generation + ".json")
    evidence = {"status": record, "reason": "OWNER_EXITED", "observed_birth": actual}
    if archive.exists():
        prior = core.read_json(archive)
        if prior.get("status") != record or prior.get("reason") != "OWNER_EXITED":
            raise PermissionError("Markdownify crash history changed")
    else:
        core.write_json(archive, evidence)
    core.write_json(core.STATE / STATUS_RECORD, {RETIRED_GENERATION: generation})


def _start(root):
    value = specification(root)
    with core.LifetimeLock(core.STATE / TRANSITION_LOCK):
        marker = core.STATE / STOP_REQUEST
        if marker.exists():
            record = core.read_json(core.STATE / STATUS_RECORD)
            _retire_stopped_record(record, core.read_json(marker))
            marker.unlink()
        else:
            _retire_crashed_record(_optional_status_record())
    ensure(root)
    print(json.dumps({"ready": True, "id": value["id"]}))


def _stop(root):
    specification(root, for_stop=True)
    with core.LifetimeLock(core.STATE / TRANSITION_LOCK):
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
        (p for p in (Path.cwd(), *Path.cwd().parents) if os.path.lexists(p / ".git")),
        None,
    )
    if root is None:
        raise PermissionError("No session workspace")
    roots.physical_root(root)
    return root


def _run(argv=None):
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
        print(
            json.dumps(
                {"prepared": True, "id": value["id"], "endpoint": "allocated_on_start"}
            )
        )
    elif args.mode == "serve":
        serve(args.root)
    elif args.mode == "start":
        _start(root=args.root)
    elif args.mode == "stop":
        _stop(root=args.root)
    else:
        value = specification(args.root)
        print(json.dumps(request(value, "GET", HEALTH_PATH)[0]))


def main(argv=None):
    try:
        result = _run(argv)
        return 0 if result is None else result
    except Exception:
        sys.stderr.write(
            "Safe Markdownify operation refused; no credential or fallback exposed."
            + "\n"
        )
        return 64


if __name__ == "__main__":
    raise SystemExit(main())
