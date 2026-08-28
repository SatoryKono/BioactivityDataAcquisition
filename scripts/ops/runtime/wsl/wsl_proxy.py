"""Minimal HTTP CONNECT proxy for WSL2 -> Windows VPN tunnel.

Listens on loopback by default. To expose the proxy to the WSL virtual network,
explicitly supply the Windows host address for that interface with --listen-host.
Wildcard addresses are intentionally rejected.

Usage:
    python scripts/ops/runtime/wsl/wsl_proxy.py
    python scripts/ops/runtime/wsl/wsl_proxy.py --listen-host <wsl-host-ip>
    pythonw scripts/ops/runtime/wsl/wsl_proxy.py
"""

from __future__ import annotations

import argparse
import ipaddress
import logging
import select
import socket
import threading
from urllib.parse import urlsplit

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 3128
BUFFER_SIZE = 65536
CONNECT_TIMEOUT = 10

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("wsl-proxy")


def relay(src: socket.socket, dst: socket.socket) -> None:
    """Bidirectional byte relay between two sockets."""
    try:
        while True:
            readable, _, _ = select.select([src, dst], [], [], 60)
            if not readable:
                break
            for sock in readable:
                data = sock.recv(BUFFER_SIZE)
                if not data:
                    return
                peer = dst if sock is src else src
                peer.sendall(data)
    except (OSError, ConnectionResetError):
        pass
    finally:
        src.close()
        dst.close()


def handle_connect(client: socket.socket, host: str, port: int) -> None:
    """Handle CONNECT method (HTTPS tunneling)."""
    try:
        remote = socket.create_connection((host, port), timeout=CONNECT_TIMEOUT)
    except OSError as exc:
        client.sendall(f"HTTP/1.1 502 Bad Gateway\r\n\r\n{exc}\r\n".encode())
        client.close()
        return

    client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
    log.info("CONNECT %s:%d", host, port)
    relay(client, remote)


def handle_plain(client: socket.socket, method: str, url: str, rest: bytes) -> None:
    """Forward plain HTTP request."""
    parsed_url = urlsplit(url)
    if parsed_url.scheme:
        if parsed_url.scheme != "http":
            client.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\nUnsupported scheme\r\n")
            client.close()
            return
        host_port = parsed_url.netloc
        path = parsed_url.path or "/"
        if parsed_url.query:
            path = f"{path}?{parsed_url.query}"
    else:
        slash = url.find("/")
        if slash == -1:
            host_port, path = url, "/"
        else:
            host_port, path = url[:slash], url[slash:]

    if ":" in host_port:
        host, port_text = host_port.rsplit(":", 1)
        port = int(port_text)
    else:
        host, port = host_port, 80

    try:
        remote = socket.create_connection((host, port), timeout=CONNECT_TIMEOUT)
    except OSError as exc:
        client.sendall(f"HTTP/1.1 502 Bad Gateway\r\n\r\n{exc}\r\n".encode())
        client.close()
        return

    request_line = f"{method} {path} HTTP/1.1\r\n".encode()
    remote.sendall(request_line + rest)
    log.info("%s %s:%d%s", method, host, port, path)
    relay(client, remote)


def handle_client(client: socket.socket, addr: tuple[str, int]) -> None:
    """Parse first line and dispatch."""
    try:
        data = client.recv(BUFFER_SIZE)
        if not data:
            client.close()
            return

        line_end = data.find(b"\r\n")
        if line_end == -1:
            client.close()
            return

        first_line = data[:line_end].decode("utf-8", errors="replace")
        parts = first_line.split()
        if len(parts) < 2:
            client.close()
            return

        method, target = parts[0], parts[1]

        if method.upper() == "CONNECT":
            if ":" in target:
                host, port_text = target.rsplit(":", 1)
                port = int(port_text)
            else:
                host, port = target, 443
            while b"\r\n\r\n" not in data:
                more = client.recv(BUFFER_SIZE)
                if not more:
                    break
                data += more
            handle_connect(client, host, port)
            return

        rest = data[line_end + 2 :]
        handle_plain(client, method, target, rest)
    except Exception:
        log.exception("Error handling %s", addr)
        client.close()


def _parse_listen_settings(argv: list[str] | None = None) -> tuple[str, int]:
    """Parse explicit non-wildcard listener settings."""
    parser = argparse.ArgumentParser(description="Run the local WSL HTTP proxy.")
    parser.add_argument("--listen-host", default=LISTEN_HOST)
    parser.add_argument("--listen-port", type=int, default=LISTEN_PORT)
    args = parser.parse_args(argv)
    try:
        listen_address = ipaddress.IPv4Address(args.listen_host)
    except ipaddress.AddressValueError:
        parser.error("listener address must be a concrete IPv4 address")
    if listen_address.is_unspecified:
        parser.error("wildcard listener addresses are not permitted")
    return str(listen_address), args.listen_port


def main(argv: list[str] | None = None) -> None:
    listen_host, listen_port = _parse_listen_settings(argv)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((listen_host, listen_port))
    server.listen(128)
    log.info("WSL proxy listening on %s:%d", listen_host, listen_port)

    try:
        while True:
            client, addr = server.accept()
            thread = threading.Thread(
                target=handle_client,
                args=(client, addr),
                daemon=True,
            )
            thread.start()
    except KeyboardInterrupt:
        log.info("Shutting down")
    finally:
        server.close()


if __name__ == "__main__":
    main()
