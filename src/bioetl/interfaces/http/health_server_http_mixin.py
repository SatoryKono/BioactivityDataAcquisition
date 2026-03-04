"""HTTP protocol and request-processing helpers for HealthServer."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Protocol, cast

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.interfaces.http.types import HealthResponse


class _RouteRequestSupport(Protocol):
    """Typed support contract for request routing implementation."""

    async def _route_request(
        self,
        writer: asyncio.StreamWriter,
        path: str,
    ) -> None: ...


class HealthServerHTTPMixin:
    """Mixin for low-level HTTP request/response lifecycle."""

    _logger: LoggerPort | None
    _request_error_allowlist: tuple[type[BaseException], ...]
    _writer_close_allowlist: tuple[type[BaseException], ...]

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle incoming HTTP connection."""
        try:
            await self._process_request(reader, writer)
        except TimeoutError:
            await self._send_response(writer, 408, "Request Timeout")
        except self._request_error_allowlist as error:
            await self._handle_request_error(writer, error)
        finally:
            await self._close_writer(writer)

    async def _process_request(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Process incoming HTTP request."""
        request_line = await asyncio.wait_for(reader.readline(), timeout=5.0)
        if not request_line:
            return

        method, path = self._parse_request_line(request_line)
        if method is None or path is None:
            await self._send_response(writer, 400, "Bad Request")
            return

        await self._consume_headers(reader)

        if method != "GET":
            await self._send_response(writer, 405, "Method Not Allowed")
            return

        route_support = cast(_RouteRequestSupport, self)
        await route_support._route_request(writer, path)

    def _parse_request_line(self, request_line: bytes) -> tuple[str | None, str | None]:
        """Parse HTTP request line into method and path."""
        request = request_line.decode("utf-8").strip()
        parts = request.split(" ")
        if len(parts) < 2:
            return None, None
        return parts[0], parts[1]

    async def _consume_headers(self, reader: asyncio.StreamReader) -> None:
        """Read and discard HTTP headers."""
        while True:
            line = await reader.readline()
            if line in (b"\r\n", b"\n", b""):
                break

    async def _handle_request_error(
        self,
        writer: asyncio.StreamWriter,
        error: BaseException,
    ) -> None:
        """Handle request processing error."""
        if self._logger:
            self._logger.error(
                "health_server_error",
                error=str(error),
                error_type=type(error).__name__,
                reason="request_processing_failed",
                reason_code="HEALTH_REQUEST_PROCESSING_FAILED",
            )
        await self._send_response(writer, 500, "Internal Server Error")

    async def _close_writer(self, writer: asyncio.StreamWriter) -> None:
        """Close the stream writer safely."""
        try:
            writer.close()
            await writer.wait_closed()
        except self._writer_close_allowlist as close_error:
            if self._logger:
                self._logger.debug(
                    "health_server_writer_close_failed",
                    error=str(close_error),
                    error_type=type(close_error).__name__,
                    reason="writer_close_failed",
                    reason_code="HEALTH_WRITER_CLOSE_FAILED",
                )

    async def _send_json_response(
        self,
        writer: asyncio.StreamWriter,
        response: HealthResponse,
    ) -> None:
        """Send JSON response."""
        body = response.to_json()
        status_code = response.http_status
        status_text = "OK" if status_code == 200 else "Service Unavailable"
        http_response = (
            f"HTTP/1.1 {status_code} {status_text}\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n"
            "\r\n"
            f"{body}"
        )
        writer.write(http_response.encode("utf-8"))
        await writer.drain()

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        message: str,
    ) -> None:
        """Send plain-text JSON error response."""
        body = json.dumps({"error": message})
        http_response = (
            f"HTTP/1.1 {status_code} {message}\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n"
            "\r\n"
            f"{body}"
        )
        writer.write(http_response.encode("utf-8"))
        await writer.drain()


__all__ = ["HealthServerHTTPMixin"]
