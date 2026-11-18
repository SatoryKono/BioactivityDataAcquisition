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
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
HOST = Path("D:/pc-agent/tools/shared-mcp")
PYTHON = Path("C:/Users/Fedor/AppData/Local/Programs/Python/Python313/python.exe")
SITE = "D:/github/BioactivityDataAcquisition/.venv-win/Lib/site-packages"
sys.path.append(SITE)
import psutil


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


core = module("markdownify_primitives", HOST / "supervisor.py")
scope = module("markdownify_scope", HOST / "project-memory-scope.py")
roots = module("markdownify_roots", HOST / "ast-workspace-profile.py")
files = module("markdownify_safe_file", HERE / "safe_file.py")
EXTENSIONS = {"pdf-to-markdown": ".pdf", "docx-to-markdown": ".docx", "pptx-to-markdown": ".pptx",
              "xlsx-to-markdown": ".xlsx", "html-to-markdown": ".html", "get-markdown-file": ".md"}
TOOLS = [{"name": name, "description": "Read or convert a handle-verified project file",
          "inputSchema": {"type": "object", "properties": {"filepath": {"type": "string"}},
                          "required": ["filepath"], "additionalProperties": False},
          "annotations": {"readOnlyHint": True, "openWorldHint": False}}
         for name in EXTENSIONS]


def identity(root):
    root = roots.physical_root(root)
    value = {"schema": 1, "root": str(root), "account": scope.account_sid(),
             "device": root.stat().st_dev, "inode": root.stat().st_ino,
             "git_common": str(roots.CANONICAL / ".git")}
    return hashlib.sha256(scope.canonical(value)).hexdigest(), value


def configure(root):
    key, binding = identity(root)
    core.STATE = Path.home() / "AppData/Local/pc-agent/mcp-shared/markdownify-bioetl-v1" / key
    return key, binding


def pins(converter):
    paths = [HERE / "safe_markdownify.py", HERE / "safe_file.py", HOST / "supervisor.py",
             HOST / "project-memory-scope.py", HOST / "ast-workspace-profile.py", PYTHON, Path(converter)]
    return {str(path): core.sha(path) for path in paths}


def specification(root):
    key, binding = configure(root)
    spec = core.read_json(core.STATE / "profile.json")
    if spec["id"] != key or spec["binding"] != binding or spec["pins"] != pins(spec["converter"]):
        raise PermissionError("Markdownify profile/runtime drift")
    return spec


def prepare(root):
    key, binding = configure(root)
    core.private_directory()
    with core.LifetimeLock(core.STATE / "transition.lock"):
        path = core.STATE / "profile.json"
        if path.exists():
            return specification(root)
        if any(core.STATE.iterdir()):
            if any(p.name != "transition.lock" for p in core.STATE.iterdir()):
                raise PermissionError("Incomplete Markdownify profile; no overwrite")
        converter = json.loads((HOST / "host-servers.json").read_bytes())["host_services"]["markdownify"]["markitdown_path"]
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        spec = {"id": key, "binding": binding, "port": port, "converter": converter, "pins": pins(converter)}
        core.credential(create=True)
        core.write_json(path, spec)
        return spec


def request(spec, method, path, body=None, session=None):
    record = core.read_json(core.STATE / "status.json")
    if core.process_birth(record["owner_pid"]) != record["owner_birth"]:
        raise PermissionError("Markdownify owner identity unavailable")
    connection = http.client.HTTPConnection("127.0.0.1", spec["port"], timeout=100)
    connection.connect()
    local_port = connection.sock.getsockname()[1]
    matched = [row for row in psutil.net_connections(kind="tcp")
               if row.status == "ESTABLISHED" and row.laddr.ip == "127.0.0.1"
               and row.laddr.port == spec["port"] and row.raddr
               and row.raddr.port == local_port]
    if not matched or any(row.pid != record["owner_pid"] for row in matched):
        connection.close()
        raise PermissionError("Markdownify socket identity unavailable")
    headers = {"Authorization": "Bearer " + core.credential(), "Content-Type": "application/json"}
    if session:
        headers["Mcp-Session-Id"] = session
    try:
        connection.request(method, path, json.dumps(body) if body is not None else None, headers)
        response = connection.getresponse()
        data = response.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024 or response.status >= 400:
            raise PermissionError("Markdownify request refused; no replay")
        return (json.loads(data) if data else None), response.getheader("Mcp-Session-Id")
    finally:
        connection.close()


def ensure(root):
    spec = specification(root)
    launched = False
    for _ in range(160):
        record = core.read_json(core.STATE / "status.json") if (core.STATE / "status.json").exists() else {}
        pid, birth = record.get("owner_pid"), record.get("owner_birth")
        if pid and core.process_birth(pid) == birth:
            try:
                health, _ = request(spec, "GET", "/health")
                if health["ready"] and health["generation"] == record["generation"]:
                    return spec
            except (OSError, PermissionError):
                pass
        elif pid and psutil.pid_exists(pid):
            raise PermissionError("Reused or unknown Markdownify PID")
        else:
            with core.LifetimeLock(core.STATE / "transition.lock"):
                current = core.read_json(core.STATE / "status.json") if (core.STATE / "status.json").exists() else {}
                if current != record:
                    continue
                if launched:
                    raise PermissionError("Markdownify exited during startup; no launch loop")
                child = subprocess.Popen([str(PYTHON), "-I", "-S", "-B", str(HERE / "safe_markdownify.py"),
                                          "serve", "--root", str(root)], cwd=HERE,
                                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                         creationflags=core.WINDOWS_HIDE | subprocess.CREATE_NEW_PROCESS_GROUP)
                birth = core.process_birth(child.pid)
                if birth is None:
                    raise PermissionError("Markdownify launch identity unknown")
                core.write_json(core.STATE / "status.json", {"owner_pid": child.pid, "owner_birth": birth,
                                                            "generation": uuid.uuid4().hex})
                launched = True
        time.sleep(0.2)
    raise TimeoutError("Markdownify startup deadline; no fallback")


def convert(spec, name, args):
    if name not in EXTENSIONS or set(args) != {"filepath"}:
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
    env = {key: value for key, value in os.environ.items()
           if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP", "PATHEXT"}}
    env["PYTHONUTF8"] = "1"
    owned = core.Job()
    child = None
    try:
        child = subprocess.Popen([spec["converter"], str(snapshot)], cwd=job, env=env,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 creationflags=core.WINDOWS_HIDE)
        owned.attach(child)
        output, _ = child.communicate(timeout=90)
        if child.returncode or len(output) > 1024 * 1024:
            raise ValueError("Conversion failed or exceeded output bound")
        return output.decode("utf-8")
    finally:
        owned.close()
        if child and child.poll() is None:
            child.wait(timeout=10)
        snapshot.unlink()
        job.rmdir()


def serve(root):
    spec = specification(root)
    with core.LifetimeLock(core.STATE / "owner.lock"):
        # Parent publishes PID+birth before this process binds the port.
        for _ in range(100):
            if (core.STATE / "status.json").is_file():
                record = core.read_json(core.STATE / "status.json")
                if record.get("owner_pid") == os.getpid() and record.get("owner_birth") == core.process_birth(os.getpid()):
                    break
            time.sleep(.05)
        else:
            raise PermissionError("Markdownify launch was not published")
        token = core.credential()
        sessions = set()
        gate = threading.Lock()

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def reply(self, status, value=None, session=None):
                raw = json.dumps(value).encode() if value is not None else b""
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                if session:
                    self.send_header("Mcp-Session-Id", session)
                self.end_headers()
                self.wfile.write(raw)

            def authorized(self):
                if not secrets.compare_digest(self.headers.get("Authorization", ""), "Bearer " + token):
                    self.reply(401)
                    return False
                specification(root)
                return True

            def do_GET(self):
                if self.authorized() and self.path == "/health":
                    self.reply(200, {"ready": True, "service": "markdownify-bioetl", "generation": record["generation"]})
                elif self.path != "/health":
                    self.reply(405)

            def do_DELETE(self):
                if self.authorized():
                    sessions.discard(self.headers.get("Mcp-Session-Id"))
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
                identifier = request_value.get("id")
                method = request_value.get("method")
                session = self.headers.get("Mcp-Session-Id")
                if method == "initialize":
                    session = uuid.uuid4().hex
                    sessions.add(session)
                    result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                              "serverInfo": {"name": "markdownify-bioetl", "version": "1.0.0"}}
                elif session not in sessions:
                    self.reply(404)
                    return
                elif identifier is None:
                    self.reply(202)
                    return
                elif method == "tools/list":
                    result = {"tools": TOOLS}
                elif method == "ping":
                    result = {}
                elif method == "tools/call":
                    with gate:
                        try:
                            params = request_value["params"]
                            text = convert(spec, params["name"], params.get("arguments", {}))
                            result = {"content": [{"type": "text", "text": text}]}
                        except Exception:
                            result = {"isError": True, "content": [{"type": "text", "text": "Local file access/conversion refused"}]}
                else:
                    self.reply(200, {"jsonrpc": "2.0", "id": identifier, "error": {"code": -32601, "message": "Unsupported method"}})
                    return
                self.reply(200, {"jsonrpc": "2.0", "id": identifier, "result": result}, session)

        server = ThreadingHTTPServer(("127.0.0.1", spec["port"]), Handler)
        server.daemon_threads = True
        server.serve_forever(poll_interval=.2)


def client(root):
    spec = ensure(root)
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "serve", "status", "client"))
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()
    if args.mode == "client":
        if args.root is not None:
            raise PermissionError("Client root override is forbidden")
        root = next((p for p in (Path.cwd(), *Path.cwd().parents) if (p / ".git").exists()), None)
        if root is None:
            raise PermissionError("No session workspace")
        roots.physical_root(root)
        client(root)
    elif args.root is None:
        raise ValueError("Administrative root required")
    elif args.mode == "prepare":
        value = prepare(args.root)
        print(json.dumps({"prepared": True, "id": value["id"], "port": value["port"]}))
    elif args.mode == "serve":
        serve(args.root)
    else:
        value = specification(args.root)
        print(json.dumps(request(value, "GET", "/health")[0]))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.stderr.write("Safe Markdownify operation refused; no credential or fallback exposed.\n")
        raise SystemExit(64) from None
