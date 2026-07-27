#!/usr/bin/env python3
"""Forward one Windows Docker MCP streaming gateway to WSL loopback."""

from __future__ import annotations

import argparse
import select
import signal
import socket
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path


def _port_is_open(port: int) -> bool:
    """Probe whether Windows loopback is accepting TCP on ``port``.

    Uses a PowerShell TcpClient from WSL so the check sees the Windows network
    stack (where Docker MCP gateway listens), not the Linux/WSL stack alone.
    """
    probe = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            (
                "$c=[Net.Sockets.TcpClient]::new();"
                f"try{{$c.Connect('127.0.0.1',{port});$c.Close();exit 0}}"
                "catch{exit 1}"
            ),
        ],
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
    raise TimeoutError(f"Windows Docker MCP did not listen on 127.0.0.1:{port}")


class _ForwardHandler(socketserver.BaseRequestHandler):
    remote_port: int
    relay_script: str

    def handle(self) -> None:
        relay = subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-File",
                self.relay_script,
                "-Port",
                str(self.remote_port),
            ],
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
    args = parser.parse_args()

    relay_script = Path(__file__).with_name("windows_tcp_relay.ps1")
    child = subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            (
                "docker mcp gateway run "
                f"--servers {args.server} --transport streaming "
                f"--host 127.0.0.1 --port {args.remote_port} "
                "--allow-unauthenticated"
            ),
        ],
        close_fds=True,
    )
    stopped = threading.Event()

    def stop(_signum: int, _frame: object) -> None:
        stopped.set()
        child.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        _wait_for_port(args.remote_port, args.startup_timeout)
        _ForwardHandler.remote_port = args.remote_port
        _ForwardHandler.relay_script = str(relay_script)
        with _ForwardServer(("127.0.0.1", args.local_port), _ForwardHandler) as server:
            server.timeout = 1
            while not stopped.is_set() and child.poll() is None:
                server.handle_request()
        return child.poll() or 0
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()


if __name__ == "__main__":
    sys.exit(main())
