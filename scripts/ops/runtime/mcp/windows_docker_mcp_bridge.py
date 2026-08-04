#!/usr/bin/env python3
"""Forward one Windows-native MCP streaming server to WSL loopback."""

from __future__ import annotations

import argparse
import re
import select
import signal
import socket
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

_SERVER_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_POWERSHELL_EXE = "powershell.exe"
_BACKEND_DOCKER_GATEWAY = "docker-gateway"
_BACKEND_MERMAID_NPX = "mermaid-npx"
_SUPPORTED_BACKENDS = (_BACKEND_DOCKER_GATEWAY, _BACKEND_MERMAID_NPX)


def _validated_port(port: int) -> int:
    if not isinstance(port, int) or not (1 <= port <= 65535):
        raise ValueError(f"invalid TCP port: {port!r}")
    return port


def _validated_server_name(name: str) -> str:
    if not _SERVER_NAME_RE.fullmatch(name):
        raise ValueError(f"invalid MCP server name: {name!r}")
    return name


def _port_is_open(port: int) -> bool:
    """Probe whether Windows loopback is accepting TCP on ``port``.

    Uses a PowerShell TcpClient from WSL so the check sees the Windows network
    stack (where Docker MCP gateway listens), not the Linux/WSL stack alone.
    """
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    safe_port = _validated_port(port)
    # Port is validated numeric — interpolated only into a fixed Connect call.
    command = ensure_safe_cli_argv(
        [_POWERSHELL_EXE, "-NoLogo", "-NonInteractive", "-NoProfile", "-Command"]
    )
    command.append(
        "$c=[Net.Sockets.TcpClient]::new();"
        f"try{{$c.Connect('127.0.0.1',{safe_port});$c.Close();exit 0}}"
        "catch{exit 1}"
    )
    probe = subprocess.run(  # NOSONAR - argv sanitized; port validated int
        command,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return probe.returncode == 0


def _wait_for_port(port: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _port_is_open(port):
            return
        time.sleep(0.5)
    raise TimeoutError(f"Windows MCP backend did not listen on 127.0.0.1:{port}")


def _as_windows_path(path: Path) -> str:
    """Translate a WSL path before passing it to Windows PowerShell ``-File``.

    ``wslpath -w`` expects a Linux-style path with forward slashes. Using
    ``str(Path(...))`` on a Windows-hosted pytest/runtime rewrites separators to
    backslashes (e.g. ``\\mnt\\e\\...``), which breaks the probe. Always pass
    the POSIX form.
    """
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    completed = subprocess.run(
        ensure_safe_cli_argv(["wslpath", "-w", path.as_posix()]),
        check=True,
        capture_output=True,
        text=True,
    )
    translated = completed.stdout.strip()
    if not translated:
        raise RuntimeError(f"wslpath returned an empty path for {path}")
    return translated


def _windows_backend_command(
    *, server: str, remote_port: int, backend: str
) -> list[str]:
    """Build validated Windows backend argv for one shared endpoint."""
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    safe_server = _validated_server_name(server)
    safe_port = _validated_port(remote_port)
    prefix = [_POWERSHELL_EXE, "-NoLogo", "-NonInteractive", "-NoProfile"]
    if backend == _BACKEND_MERMAID_NPX:
        if safe_server != "mermaid":
            raise ValueError("mermaid-npx backend is valid only for server 'mermaid'")
        wrapper = (
            Path(__file__).resolve().parents[4]
            / "scripts"
            / "ai"
            / "mcp"
            / "mcp_mermaid_wrapper.ps1"
        )
        return ensure_safe_cli_argv(
            [
                *prefix,
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                _as_windows_path(wrapper),
                "-Transport",
                "streamable",
                "-BindHost",
                "127.0.0.1",
                "-Port",
                str(safe_port),
                "-Endpoint",
                "/mcp",
            ]
        )
    if backend != _BACKEND_DOCKER_GATEWAY:
        raise ValueError(f"unsupported Windows MCP backend: {backend!r}")
    return ensure_safe_cli_argv(
        [
            *prefix,
            "-Command",
            (
                "docker mcp gateway run "
                f"--servers {safe_server} --transport streaming "
                f"--host 127.0.0.1 --port {safe_port} "
                "--allow-unauthenticated"
            ),
        ]
    )


class _ForwardHandler(socketserver.BaseRequestHandler):
    remote_port: int
    relay_script: str

    def handle(self) -> None:
        from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

        safe_port = _validated_port(int(self.remote_port))
        command = ensure_safe_cli_argv(
            [
                _POWERSHELL_EXE,
                "-NoLogo",
                "-NonInteractive",
                "-NoProfile",
                "-File",
                self.relay_script,
                "-Port",
                str(safe_port),
            ]
        )
        relay = subprocess.Popen(  # NOSONAR - argv sanitized; port validated
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        assert relay.stdin is not None
        assert relay.stdout is not None
        try:
            sockets = [self.request, relay.stdout]
            while True:
                readable, _, _ = select.select(sockets, [], [], 30)
                if not readable:
                    continue
                for source in readable:
                    data = (
                        source.recv(65536)
                        if source is self.request
                        else source.read(65536)
                    )
                    if not data:
                        return
                    if source is self.request:
                        relay.stdin.write(data)
                        relay.stdin.flush()
                    else:
                        self.request.sendall(data)
        finally:
            relay.terminate()


class _ForwardServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--local-port", type=int, required=True)
    parser.add_argument("--remote-port", type=int, required=True)
    parser.add_argument("--startup-timeout", type=float, default=120)
    parser.add_argument(
        "--backend", choices=_SUPPORTED_BACKENDS, default=_BACKEND_DOCKER_GATEWAY
    )
    args = parser.parse_args()
    server = _validated_server_name(str(args.server))
    remote_port = _validated_port(int(args.remote_port))
    local_port = _validated_port(int(args.local_port))
    args.server = server
    args.remote_port = remote_port
    args.local_port = local_port

    relay_script = Path(__file__).with_name("windows_tcp_relay.ps1")
    command = _windows_backend_command(
        server=server, remote_port=remote_port, backend=str(args.backend)
    )
    # A previous WSL bridge can disappear while the Windows-side MCP backend
    # remains alive. Reuse it instead of racing a second backend on the port.
    child: subprocess.Popen[bytes] | None = None
    if not _port_is_open(args.remote_port):
        child = subprocess.Popen(  # NOSONAR - argv sanitized; server/port validated
            command,
            close_fds=True,
        )
    stopped = threading.Event()

    def stop(_signum: int, _frame: object) -> None:
        stopped.set()
        if child is not None:
            child.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        _wait_for_port(args.remote_port, args.startup_timeout)
        _ForwardHandler.remote_port = args.remote_port
        _ForwardHandler.relay_script = _as_windows_path(relay_script)
        with _ForwardServer(("127.0.0.1", args.local_port), _ForwardHandler) as server:
            server.timeout = 1
            while not stopped.is_set() and (child is None or child.poll() is None):
                server.handle_request()
        return 0 if child is None else child.poll() or 0
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()


if __name__ == "__main__":
    sys.exit(main())
