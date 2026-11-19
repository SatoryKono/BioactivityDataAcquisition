"""Linux port of the reviewed pc-agent public-fetch-v1 network boundary.

Original pinned-public-egress.py SHA-256:
854cb17f4f4d36e7c63e3cb167d3f0cf1b509d0aad282052817d45fec0471c51.
The registered Windows owner and its runtime remain independent.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
import ipaddress
import socket
import time
from importlib.metadata import version

import anyio
import httpcore
import httpx

PINS = {"httpcore": "1.0.9", "httpx": "0.28.1", "anyio": "4.16.0"}
MAX_BODY_BYTES = 2 * 1024 * 1024
BODY_SECONDS = 15
Resolver = Callable[[str], Awaitable[list[str]]]
AddressPolicy = Callable[[str], bool]
SocketOptions = Iterable[tuple[int, int, int | bytes]]


class PublicBackend(httpcore.AsyncNetworkBackend):
    def __init__(
        self,
        resolve: Resolver,
        permitted: AddressPolicy,
        backend: httpcore.AsyncNetworkBackend | None = None,
    ) -> None:
        self.resolve = resolve
        self.permitted = permitted
        self.backend = backend if backend is not None else httpcore.AnyIOBackend()

    async def public_addresses(
        self, host: str
    ) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        try:
            ipaddress.ip_address(host)
        except ValueError:
            addresses = await self.resolve(host)
        else:
            addresses = [host]
        if not addresses or len(addresses) > 32:
            raise httpcore.ConnectError("Invalid number of destination addresses")
        if not all(
            isinstance(item, str) and "%" not in item and self.permitted(item)
            for item in addresses
        ):
            raise httpcore.ConnectError(
                "Destination has an address outside the public profile"
            )
        return list(dict.fromkeys(ipaddress.ip_address(item) for item in addresses))

    async def verify_peer(
        self,
        stream: httpcore.AsyncNetworkStream,
        address: ipaddress.IPv4Address | ipaddress.IPv6Address,
        port: int,
    ) -> None:
        try:
            peer = stream.get_extra_info("server_addr")
            if not peer or ipaddress.ip_address(peer[0]) != address or peer[1] != port:
                raise httpcore.ConnectError(
                    "Connected peer differs from validated destination"
                )
        except (ValueError, TypeError, IndexError, httpcore.ConnectError):
            await stream.aclose()
            raise httpcore.ConnectError(
                "Connected peer could not be verified"
            ) from None

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: SocketOptions | None = None,
    ) -> httpcore.AsyncNetworkStream:
        if port not in {80, 443} or local_address is not None:
            raise httpcore.ConnectError(
                "Port or local address not allowed by this public profile"
            )
        try:
            with anyio.fail_after(10 if timeout is None else min(10, timeout)):
                canonical = await self.public_addresses(host)
                failure = None
                for address in canonical:
                    try:
                        # Pass only the validated literal, never the DNS name.
                        # HTTPCore keeps the original origin for Host and TLS.
                        stream = await self.backend.connect_tcp(
                            str(address), port, socket_options=socket_options
                        )
                    except (httpcore.ConnectError, httpcore.ConnectTimeout) as error:
                        failure = error
                        continue
                    await self.verify_peer(stream, address, port)
                    return stream
                raise httpcore.ConnectError(
                    "No verified public connection"
                ) from failure
        except (ValueError, socket.gaierror) as error:
            raise httpcore.ConnectError(
                "Could not resolve a public destination"
            ) from error
        except TimeoutError as error:
            raise httpcore.ConnectTimeout("Public connection deadline") from error

    async def connect_unix_socket(
        self, *_args: object, **_kwargs: object
    ) -> httpcore.AsyncNetworkStream:
        raise httpcore.ConnectError("Unix socket connections are disabled")

    async def sleep(self, seconds: float) -> None:
        await anyio.sleep(seconds)


class BoundedBody(httpx.AsyncByteStream):
    def __init__(self, stream: httpx.AsyncByteStream, request: httpx.Request) -> None:
        self.stream = stream
        self.request = request

    async def __aiter__(self) -> AsyncIterator[bytes]:
        iterator = self.stream.__aiter__()
        deadline = time.monotonic() + BODY_SECONDS
        size = 0
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                with anyio.fail_after(remaining):
                    chunk = await anext(iterator)
                size += len(chunk)
                if size > MAX_BODY_BYTES:
                    raise httpx.ReadError(
                        "Response body exceeds the public fetch limit",
                        request=self.request,
                    )
                yield chunk
        except StopAsyncIteration:
            return
        except TimeoutError as error:
            raise httpx.ReadTimeout(
                "Response body deadline", request=self.request
            ) from error

    async def aclose(self) -> None:
        await self.stream.aclose()


class BoundedTransport(httpx.AsyncHTTPTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        # This runs for every redirect as well as the initial request.
        if (
            request.url.scheme not in {"http", "https"}
            or request.url.userinfo
            or request.url.port not in {None, 80, 443}
        ):
            raise httpx.UnsupportedProtocol(
                "Destination outside the public profile", request=request
            )
        request.headers["Accept-Encoding"] = "identity"
        response = await super().handle_async_request(request)
        encoding = response.headers.get("Content-Encoding", "").strip().lower()
        declared = response.headers.get("Content-Length")
        if encoding not in {"", "identity"} or (
            declared is not None
            and (
                not declared.isascii()
                or not declared.isdigit()
                or len(declared) > 10
                or int(declared) > MAX_BODY_BYTES
            )
        ):
            await response.aclose()
            raise httpx.ReadError(
                "Encoded or oversized response refused", request=request
            )
        response.stream = BoundedBody(response.stream, request)
        return response


class PublicClient(httpx.AsyncClient):
    async def send(self, request: httpx.Request, **kwargs: object) -> httpx.Response:
        try:
            with anyio.fail_after(35):
                return await super().send(request, **kwargs)
        except TimeoutError as error:
            raise httpx.ReadTimeout(
                "Public fetch request deadline", request=request
            ) from error


def client_factory(
    resolve: Resolver, permitted: AddressPolicy
) -> Callable[[str | None], PublicClient]:
    if any(version(package) != expected for package, expected in PINS.items()):
        raise RuntimeError("Pinned transport dependency changed")

    def make_client(proxy_url: str | None) -> PublicClient:
        if proxy_url is not None:
            raise ValueError("Explicit proxies are disabled for this public profile")
        transport = BoundedTransport(
            trust_env=False,
            retries=0,
            limits=httpx.Limits(max_keepalive_connections=0, max_connections=4),
        )
        # HTTPX 0.28.1 does not expose network_backend on AsyncHTTPTransport.
        # Fail on drift; do not fall back to HTTPX's normal DNS path.
        pool = transport._pool
        if type(pool) is not httpcore.AsyncConnectionPool or not hasattr(
            pool, "_network_backend"
        ):
            raise RuntimeError("HTTPX transport structure changed")
        pool._network_backend = PublicBackend(resolve, permitted)
        return PublicClient(transport=transport, trust_env=False, max_redirects=8)

    return make_client
