"""Routing and endpoint handlers for HealthServer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, cast

from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.interfaces.http.types import HealthResponse

if TYPE_CHECKING:
    import asyncio

    from bioetl.domain.ports import HealthMonitorPort


class _HealthResponseSupport(Protocol):
    """Typed support contract for HTTP response helpers."""

    async def _send_json_response(
        self,
        writer: asyncio.StreamWriter,
        response: HealthResponse,
    ) -> None: ...

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        message: str,
    ) -> None: ...


class _HealthStateSupport(Protocol):
    """Typed support contract for state aggregation helpers."""

    def _get_overall_status(self) -> HealthStatus: ...

    def _get_provider_statuses(
        self,
    ) -> dict[str, JsonDict]: ...  # Any: provider-specific status fields


class HealthServerRoutingMixin:
    """Mixin for health endpoint routing and payload generation."""

    _health_monitor: HealthMonitorPort | None

    @property
    def uptime_seconds(self) -> float:
        """Get server uptime in seconds."""
        raise NotImplementedError

    async def _route_request(self, writer: asyncio.StreamWriter, path: str) -> None:
        """Route request to appropriate handler."""
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
            response_support = cast(_HealthResponseSupport, self)
            await response_support._send_json_response(writer, response)
            return
        response_support = cast(_HealthResponseSupport, self)
        await response_support._send_response(writer, 404, "Not Found")

    async def _handle_health(self) -> HealthResponse:
        """Handle /health endpoint - overall health status."""
        state_support = cast(_HealthStateSupport, self)
        status = state_support._get_overall_status()
        checks: JsonDict = {  # Any: response payload values are heterogeneous
            "server": {
                "status": "healthy",
                "uptime_seconds": round(self.uptime_seconds, 2),
            }
        }
        if self._health_monitor:
            checks["providers"] = state_support._get_provider_statuses()
        return HealthResponse(
            status=status.value.lower(),
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks=checks,
        )

    async def _handle_liveness(self) -> HealthResponse:
        """Handle /health/live endpoint."""
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
        """Handle /health/ready endpoint."""
        if not self._health_monitor:
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now(tz=UTC).isoformat(),
                checks={"message": "No health monitor configured"},
            )
        state_support = cast(_HealthStateSupport, self)
        provider_statuses = state_support._get_provider_statuses()
        has_unhealthy = any(
            status.get("status") == "unhealthy" for status in provider_statuses.values()
        )
        status = "unhealthy" if has_unhealthy else "healthy"
        return HealthResponse(
            status=status,
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks={"providers": provider_statuses},
        )

    async def _handle_providers(self) -> HealthResponse:
        """Handle /health/providers endpoint."""
        if not self._health_monitor:
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now(tz=UTC).isoformat(),
                checks={"message": "No health monitor configured"},
            )
        state_support = cast(_HealthStateSupport, self)
        return HealthResponse(
            status=state_support._get_overall_status().value.lower(),
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks={"providers": state_support._get_provider_statuses()},
        )


__all__ = ["HealthServerRoutingMixin"]
