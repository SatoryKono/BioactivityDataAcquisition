# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""HTTP protocol and request-processing helpers for HealthServer."""

from __future__ import annotations

import asyncio
import json
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Protocol, cast

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

    _logger: LoggerPort | None = cast(Any, None)  # Any: host attr default (PD3)
    # Safe empty defaults so bare mixin use never raises TypeError on except.
    # Concrete HealthServer overwrites with the real allowlists in __init__.
    _request_error_allowlist: tuple[type[BaseException], ...] = ()
    _writer_close_allowlist: tuple[type[BaseException], ...] = ()
    _request_line_timeout_seconds: float = 5.0
    _header_line_timeout_seconds: float = 5.0
    _max_header_lines: int = 100
    _writer_close_timeout_seconds: float = 1.0

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle incoming HTTP connection.

        Args:
            reader: Async stream reader for the incoming TCP connection.
            writer: Async stream writer for sending the HTTP response.
        """
        try:
            await self._process_request(reader, writer)
        except TimeoutError:
            await self._send_response(writer, 408, "Request Timeout")
        except self._request_error_allowlist as error:
            await self._handle_request_error(writer, error)
        except (ConnectionError, OSError, ValueError, UnicodeDecodeError) as error:
            await self._handle_request_error(writer, error)
        except Exception as error:
            await self._handle_request_error(writer, error)
        finally:
            await self._close_writer(writer)

    async def _process_request(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Process incoming HTTP request.

        Reads request line and headers, validates method, and dispatches to the
        appropriate route handler. Sends error responses for bad requests (400)
        and unsupported methods (405).

        Args:
            reader: Async stream reader providing the raw HTTP request bytes.
            writer: Async stream writer for sending the HTTP response.
        """
        request_line = await asyncio.wait_for(
            reader.readline(),
            timeout=self._request_line_timeout_seconds,
        )
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

        route_support = cast(_RouteRequestSupport, self)  # pyright: ignore[reportInvalidCast]
        await route_support._route_request(writer, path)

    def _parse_request_line(self, request_line: bytes) -> tuple[str | None, str | None]:
        """Parse HTTP request line into method and path.

        Args:
            request_line: Raw bytes of the HTTP request line (e.g., b'GET /health HTTP/1.1\r\n').

        Returns:
            Tuple of (method, path), or (None, None) if the line is malformed.
        """
        request = request_line.decode("utf-8").strip()
        parts = request.split(" ")
        if len(parts) < 2:
            return None, None
        return parts[0], parts[1]

    async def _consume_headers(self, reader: asyncio.StreamReader) -> None:
        """Read and discard HTTP headers.

        Args:
            reader: Async stream reader positioned after the request line.
        """
        for _ in range(self._max_header_lines):
            line = await asyncio.wait_for(
                reader.readline(),
                timeout=self._header_line_timeout_seconds,
            )
            if line in (b"\r\n", b"\n", b""):
                break
        else:
            raise ValueError("Too many request headers")

    async def _handle_request_error(
        self,
        writer: asyncio.StreamWriter,
        error: BaseException,
    ) -> None:
        """Handle request processing error.

        Logs the error with structured context and sends a 500 Internal Server Error
        response to the client.

        Args:
            writer: Async stream writer for sending the error response.
            error: Exception caught during request processing.
        """
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
        """Close the stream writer safely.

        Attempts to close the writer and drain pending data. Connection-level
        errors during close are logged at DEBUG level and suppressed to avoid
        masking the original response.

        Args:
            writer: Async stream writer to close.
        """
        try:
            writer.close()
            await asyncio.wait_for(
                writer.wait_closed(),
                timeout=self._writer_close_timeout_seconds,
            )
        except TimeoutError as close_error:
            if self._logger:
                self._logger.debug(
                    "health_server_writer_close_failed",
                    error=str(close_error),
                    error_type=type(close_error).__name__,
                    reason="writer_close_timeout",
                    reason_code="HEALTH_WRITER_CLOSE_TIMEOUT",
                )
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
        """Send JSON response.

        Serializes the HealthResponse to JSON and writes a complete HTTP/1.1
        response with Content-Type: application/json.

        Args:
            writer: Async stream writer for the outgoing response.
            response: HealthResponse to serialize and send.
        """
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

    async def _send_payload_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        payload: dict[str, object],
    ) -> None:
        """Send a generic JSON payload response."""
        body = json.dumps(payload, default=str)
        try:
            status_text = HTTPStatus(status_code).phrase
        except ValueError:
            status_text = "OK"
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

    async def _send_text_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        body: str,
        *,
        content_type: str = "text/plain; charset=utf-8",
    ) -> None:
        """Send a generic text response."""
        body_bytes = body.encode("utf-8")
        try:
            status_text = HTTPStatus(status_code).phrase
        except ValueError:
            status_text = "OK"
        http_response = (
            f"HTTP/1.1 {status_code} {status_text}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body_bytes)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode() + body_bytes
        writer.write(http_response)
        await writer.drain()

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        message: str,
    ) -> None:
        """Send plain-text JSON error response.

        Writes an HTTP/1.1 response with a JSON body containing the error message.

        Args:
            writer: Async stream writer for the outgoing response.
            status_code: HTTP status code (e.g., 400, 404, 500).
            message: Human-readable error message included in the JSON body.
        """
        body = json.dumps({"error": message})
        try:
            status_text = HTTPStatus(status_code).phrase
        except ValueError:
            status_text = "Error"
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


__all__ = ["HealthServerHTTPMixin"]
