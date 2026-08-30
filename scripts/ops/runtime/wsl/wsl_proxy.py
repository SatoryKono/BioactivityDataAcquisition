"""Minimal HTTP CONNECT proxy for WSL2 -> Windows VPN tunnel.

Defaults to loopback. To expose the proxy to the WSL virtual network,
explicitly supply the Windows host address for that interface; non-loopback
listeners require an explicit client CIDR, and wildcard binding additionally
requires an explicit opt-in flag.
Supports both HTTP CONNECT (for HTTPS) and plain HTTP forwarding.

Usage:
    python scripts/ops/runtime/wsl/wsl_proxy.py
    python scripts/ops/runtime/wsl/wsl_proxy.py --listen-host <wsl-host-ip>
    pythonw scripts/ops/runtime/wsl/wsl_proxy.py
"""

from __future__ import annotations

import argparse
import ipaddress
import logging
import argparse
import ipaddress
import select
import socket
import threading
from collections.abc import Sequence
from urllib.parse import urlsplit

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 3128
BUFFER_SIZE = 65536
CONNECT_TIMEOUT = 10
PRIVATE_BIND_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)
ALLOWED_CLIENT_NETWORKS = (
    ipaddress.ip_network("127.0.0.0/8"),
    *PRIVATE_BIND_NETWORKS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("wsl-proxy")


def parse_allow_cidrs(values: Sequence[str]) -> tuple[ipaddress.IPv4Network, ...]:
    """Parse an explicit IPv4 client allowlist."""
    networks: list[ipaddress.IPv4Network] = []
    for value in values:
        network = ipaddress.ip_network(value, strict=False)
        if not isinstance(network, ipaddress.IPv4Network):
            raise ValueError("WSL proxy currently supports IPv4 client CIDRs only")
        if not any(network.subnet_of(allowed) for allowed in ALLOWED_CLIENT_NETWORKS):
            raise ValueError(
                "client CIDRs must stay within loopback or RFC1918 private ranges"
            )
        networks.append(network)
    return tuple(networks)


def build_bind_policy(
    bind_host: str,
    *,
    allow_wildcard: bool,
    allow_cidrs: Sequence[str],
) -> tuple[str, tuple[ipaddress.IPv4Network, ...]]:
    """Validate bind scope and return the effective client allowlist."""
    address = ipaddress.ip_address(bind_host)
    if not isinstance(address, ipaddress.IPv4Address):
        raise ValueError("WSL proxy currently supports IPv4 bind addresses only")
    networks = parse_allow_cidrs(allow_cidrs)
    if address.is_unspecified and not allow_wildcard:
        raise ValueError("wildcard bind requires --allow-wildcard")
    if (
        not address.is_unspecified
        and not address.is_loopback
        and not any(address in network for network in PRIVATE_BIND_NETWORKS)
    ):
        raise ValueError("non-loopback bind must use a private WSL adapter address")
    if not address.is_loopback and not networks:
        raise ValueError("non-loopback bind requires at least one --allow-cidr")
    if (
        not address.is_unspecified
        and not address.is_loopback
        and not any(address in network for network in networks)
    ):
        raise ValueError("non-loopback bind must belong to an allowed client CIDR")
    if not networks:
        networks = (ipaddress.ip_network("127.0.0.0/8"),)
    return str(address), networks


def is_client_allowed(peer_ip: str, networks: Sequence[ipaddress.IPv4Network]) -> bool:
    """Return whether a peer belongs to the configured client allowlist."""
    try:
        address = ipaddress.ip_address(peer_ip)
    except ValueError:
        return False
    return isinstance(address, ipaddress.IPv4Address) and any(
        address in network for network in networks
    )


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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind-host", "--listen-host", dest="bind_host", default=LISTEN_HOST)
    parser.add_argument("--port", "--listen-port", dest="port", type=int, default=LISTEN_PORT)
    parser.add_argument("--allow-wildcard", action="store_true")
    parser.add_argument("--allow-cidr", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if not 1 <= args.port <= 65535:
        raise ValueError("proxy port must be between 1 and 65535")
    bind_host, allowed_networks = build_bind_policy(
        args.bind_host,
        allow_wildcard=args.allow_wildcard,
        allow_cidrs=args.allow_cidr,
    )
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((bind_host, args.port))
    server.listen(128)
    log.info(
        "WSL proxy listening on %s:%d for %s",
        bind_host,
        args.port,
        ",".join(str(network) for network in allowed_networks),
    )

    try:
        while True:
            client, addr = server.accept()
            if not is_client_allowed(addr[0], allowed_networks):
                log.warning("Rejected proxy client outside allowlist: %s", addr[0])
                client.close()
                continue
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
