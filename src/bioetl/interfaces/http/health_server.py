"""HTTP Health Server for BioETL.

Provides Kubernetes-compatible liveness and readiness probes.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from bioetl.domain.types import HealthStatus
from bioetl.interfaces.http.types import HealthResponse

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.health_monitor import ProviderHealthMonitor


class HealthServer:
    """Async HTTP server for health check endpoints.

    Provides Kubernetes-compatible health probes.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        health_monitor: ProviderHealthMonitor | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        """Initialize health server."""
        self.host = host
        self.port = port
        self._health_monitor = health_monitor
        self._logger = logger
        self._server: asyncio.Server | None = None
        self._start_time: float | None = None

    async def start(self) -> None:
        """Start the health server."""
        self._start_time = time.monotonic()
        self._server = await asyncio.start_server(
            self._handle_connection,
            self.host,
            self.port,
        )
        if self._logger:
            self._logger.info("health_server_started", host=self.host, port=self.port)

    async def stop(self) -> None:
        """Stop the health server gracefully."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            if self._logger:
                self._logger.info("health_server_stopped")

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._server is not None and self._server.is_serving()

    @property
    def uptime_seconds(self) -> float:
        """Get server uptime in seconds."""
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle incoming HTTP connection."""
        try:
            request_line = await asyncio.wait_for(reader.readline(), timeout=5.0)
            if not request_line:
                return

            request = request_line.decode("utf-8").strip()
            parts = request.split(" ")

            if len(parts) < 2:
                await self._send_response(writer, 400, "Bad Request")
                return

            method, path = parts[0], parts[1]

            # Read and discard headers
            while True:
                line = await reader.readline()
                if line == b"\r\n" or line == b"\n" or not line:
                    break

            if method != "GET":
                await self._send_response(writer, 405, "Method Not Allowed")
                return

            await self._route_request(writer, path)

        except TimeoutError:
            await self._send_response(writer, 408, "Request Timeout")
        except Exception as e:
            if self._logger:
                self._logger.error("health_server_error", error=str(e))
            await self._send_response(writer, 500, "Internal Server Error")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _route_request(self, writer: asyncio.StreamWriter, path: str) -> None:
        """Route request to appropriate handler."""
        path = path.split("?")[0]  # Remove query string
        handlers = {
            "/health": self._handle_health,
            "/healthz": self._handle_health,
            "/health/live": self._handle_liveness,
            "/health/ready": self._handle_readiness,
            "/health/providers": self._handle_providers,
        }
        handler = handlers.get(path)
        if handler:
            response = await handler()
            await self._send_json_response(writer, response)
        else:
            await self._send_response(writer, 404, "Not Found")

    async def _handle_health(self) -> HealthResponse:
        """Handle /health endpoint - overall health status."""
        status = self._get_overall_status()
        checks: dict[str, Any] = {
            "server": {
                "status": "healthy",
                "uptime_seconds": round(self.uptime_seconds, 2),
            },
        }
        if self._health_monitor:
            checks["providers"] = self._get_provider_statuses()
        return HealthResponse(
            status=status.value.lower(),
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks=checks,
        )

    async def _handle_liveness(self) -> HealthResponse:
        """Handle /health/live - Kubernetes liveness probe."""
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks={
                "server": {
                    "status": "healthy",
                    "uptime_seconds": round(self.uptime_seconds, 2),
                }
            },
        )

    async def _handle_readiness(self) -> HealthResponse:
        """Handle /health/ready - Kubernetes readiness probe."""
        if not self._health_monitor:
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now(tz=UTC).isoformat(),
                checks={"message": "No health monitor configured"},
            )
        provider_statuses = self._get_provider_statuses()
        has_unhealthy = any(
            p.get("status") == "unhealthy" for p in provider_statuses.values()
        )
        status = "unhealthy" if has_unhealthy else "healthy"
        return HealthResponse(
            status=status,
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks={"providers": provider_statuses},
        )

    async def _handle_providers(self) -> HealthResponse:
        """Handle /health/providers - detailed provider status."""
        if not self._health_monitor:
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now(tz=UTC).isoformat(),
                checks={"message": "No health monitor configured"},
            )
        return HealthResponse(
            status=self._get_overall_status().value.lower(),
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks={"providers": self._get_provider_statuses()},
        )

    def _get_overall_status(self) -> HealthStatus:
        """Get overall health status from all providers."""
        if not self._health_monitor:
            return HealthStatus.HEALTHY
        states = self._health_monitor.get_all_states()
        if not states:
            return HealthStatus.HEALTHY
        statuses = [state.status for state in states.values()]
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def _get_provider_statuses(self) -> dict[str, dict[str, Any]]:
        """Get detailed status for all providers."""
        if not self._health_monitor:
            return {}
        states = self._health_monitor.get_all_states()
        return {
            name: {
                "status": state.status.value.lower(),
                "consecutive_errors": state.consecutive_errors,
            }
            for name, state in states.items()
        }

    async def _send_json_response(
        self, writer: asyncio.StreamWriter, response: HealthResponse
    ) -> None:
        """Send JSON response."""
        body = response.to_json()
        status_code = response.http_status
        status_text = "OK" if status_code == 200 else "Service Unavailable"
        http_response = (
            f"HTTP/1.1 {status_code} {status_text}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
            f"{body}"
        )
        writer.write(http_response.encode("utf-8"))
        await writer.drain()

    async def _send_response(
        self, writer: asyncio.StreamWriter, status_code: int, message: str
    ) -> None:
        """Send plain text response."""
        body = json.dumps({"error": message})
        http_response = (
            f"HTTP/1.1 {status_code} {message}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
            f"{body}"
        )
        writer.write(http_response.encode("utf-8"))
        await writer.drain()


async def run_health_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    health_monitor: ProviderHealthMonitor | None = None,
    logger: LoggerPort | None = None,
) -> None:
    """Run the health server until interrupted."""
    server = HealthServer(
        host=host, port=port, health_monitor=health_monitor, logger=logger
    )
    await server.start()
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()


__all__ = ["HealthResponse", "HealthServer", "run_health_server"]
