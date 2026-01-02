"""HTTP Health Server for BioETL.

Provides HTTP endpoints for health checks and monitoring.
Implements Kubernetes-compatible liveness and readiness probes.

Endpoints:
- GET /health - Overall health status
- GET /health/live - Liveness probe (always returns 200 if server is running)
- GET /health/ready - Readiness probe (checks all providers)
- GET /health/providers - Detailed provider health status

Usage:
    server = HealthServer(port=8080, health_monitor=monitor)
    await server.start()
    # ... server running ...
    await server.stop()
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.health_monitor import ProviderHealthMonitor


@dataclass
class HealthResponse:
    """Health check response data."""

    status: str
    timestamp: str
    version: str = "1.0.0"
    checks: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(
            {
                "status": self.status,
                "timestamp": self.timestamp,
                "version": self.version,
                "checks": self.checks,
            },
            indent=2,
        )

    @property
    def http_status(self) -> int:
        """Return HTTP status code based on health status."""
        if self.status == "healthy":
            return 200
        elif self.status == "degraded":
            return 200  # Still operational
        else:
            return 503  # Service Unavailable


class HealthServer:
    """Async HTTP server for health check endpoints.

    Provides Kubernetes-compatible health probes and detailed
    provider health information for monitoring systems.

    Attributes:
        host: Host to bind to (default: 0.0.0.0).
        port: Port to listen on (default: 8080).
        health_monitor: Optional ProviderHealthMonitor for provider checks.
        logger: Optional logger for request logging.

    Example:
        >>> monitor = ProviderHealthMonitor(metrics=metrics)
        >>> server = HealthServer(port=8080, health_monitor=monitor)
        >>> await server.start()
        >>> # Server running on http://0.0.0.0:8080/health
        >>> await server.stop()

    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        health_monitor: ProviderHealthMonitor | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        """Initialize health server.

        Args:
            host: Host to bind to.
            port: Port to listen on.
            health_monitor: Provider health monitor for readiness checks.
            logger: Logger for request logging.

        """
        self.host = host
        self.port = port
        self._health_monitor = health_monitor
        self._logger = logger
        self._server: asyncio.Server | None = None
        self._start_time: float | None = None

    async def start(self) -> None:
        """Start the health server.

        Raises:
            OSError: If the port is already in use.

        """
        self._start_time = time.monotonic()
        self._server = await asyncio.start_server(
            self._handle_connection,
            self.host,
            self.port,
        )

        if self._logger:
            self._logger.info(
                "health_server_started",
                host=self.host,
                port=self.port,
            )

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
            request_line = await asyncio.wait_for(
                reader.readline(),
                timeout=5.0,
            )

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

    async def _route_request(
        self,
        writer: asyncio.StreamWriter,
        path: str,
    ) -> None:
        """Route request to appropriate handler."""
        # Remove query string if present
        path = path.split("?")[0]

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
            provider_statuses = self._get_provider_statuses()
            checks["providers"] = provider_statuses

        return HealthResponse(
            status=status.value.lower(),
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks=checks,
        )

    async def _handle_liveness(self) -> HealthResponse:
        """Handle /health/live endpoint - Kubernetes liveness probe.

        Returns 200 if the server is running. This is a simple check
        to verify the process is alive and can respond to requests.
        """
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks={
                "server": {
                    "status": "healthy",
                    "uptime_seconds": round(self.uptime_seconds, 2),
                },
            },
        )

    async def _handle_readiness(self) -> HealthResponse:
        """Handle /health/ready endpoint - Kubernetes readiness probe.

        Returns 200 if all providers are healthy or degraded.
        Returns 503 if any provider is unhealthy.
        """
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
        """Handle /health/providers endpoint - detailed provider status."""
        if not self._health_monitor:
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now(tz=UTC).isoformat(),
                checks={"message": "No health monitor configured"},
            )

        provider_statuses = self._get_provider_statuses()

        return HealthResponse(
            status=self._get_overall_status().value.lower(),
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks={"providers": provider_statuses},
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
        result = {}

        for name, state in states.items():
            result[name] = {
                "status": state.status.value.lower(),
                "consecutive_errors": state.consecutive_errors,
            }

        return result

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
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
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
    """Run the health server until interrupted.

    Convenience function for running the server as a standalone process.

    Args:
        host: Host to bind to.
        port: Port to listen on.
        health_monitor: Provider health monitor.
        logger: Logger for request logging.

    """
    server = HealthServer(
        host=host,
        port=port,
        health_monitor=health_monitor,
        logger=logger,
    )

    await server.start()

    try:
        # Keep server running
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()


__all__ = ["HealthResponse", "HealthServer", "run_health_server"]
