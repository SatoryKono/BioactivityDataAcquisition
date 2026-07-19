"""Routing and endpoint handlers for HealthServer."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast
from urllib.parse import parse_qs, urlsplit

from bioetl.application.runtime_clock import current_utc_time
from bioetl.application.services.quarantine_service import QuarantineService
from bioetl.domain.ports import (
    CheckpointPort,
    ClockPort,
    HealthMonitorPort,
    RunLedgerPort,
    RunManifestPort,
    WorkflowManifestPort,
)
from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.interfaces.http._health_server_routing_support import (
    dispatch_control_plane_request,
    dispatch_observability_request,
    dispatch_quarantine_request,
)
from bioetl.interfaces.http.types import HealthResponse

_NOT_FOUND_MESSAGE = "Not Found"
_PROMETHEUS_TEXT_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


class HealthServerRoutingMixin:
    """Mixin for health endpoint routing and payload generation."""

    _health_monitor: HealthMonitorPort | None
    _quarantine_service: QuarantineService | None
    _checkpoint_port: CheckpointPort | None
    _run_manifest_port: RunManifestPort | None
    _run_ledger_port: RunLedgerPort | None
    _workflow_manifest_port: WorkflowManifestPort | None
    _clock: ClockPort | None
    _data_root: str | None
    _prometheus_base_url: str

    if TYPE_CHECKING:
        # Supplied by sibling mixins in the concrete HealthServer MRO.
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

        async def _send_payload_response(
            self,
            writer: asyncio.StreamWriter,
            status_code: int,
            payload: dict[str, object],
        ) -> None: ...

        async def _send_text_response(
            self,
            writer: asyncio.StreamWriter,
            status_code: int,
            body: str,
            *,
            content_type: str = "text/plain; charset=utf-8",
        ) -> None: ...

        def _get_overall_status(self) -> HealthStatus: ...

        def _get_provider_statuses(self) -> dict[str, JsonDict]: ...

    @property
    def uptime_seconds(self) -> float:
        """Get server uptime in seconds."""
        raise NotImplementedError

    def _response_timestamp(self) -> str:
        """Return the sanctioned timestamp source for health responses."""
        if self._clock is not None:
            return cast("str", self._clock.now().isoformat())
        return cast("str", current_utc_time().isoformat())

    async def _route_request(self, writer: asyncio.StreamWriter, path: str) -> None:
        """Route request to appropriate handler."""
        parsed_path = urlsplit(path)
        route_path = parsed_path.path
        query = self._parse_query_params(parsed_path.query)
        handlers = {
            "/health": self._handle_health,
            "/healthz": self._handle_health,
            "/health/live": self._handle_liveness,
            "/health/ready": self._handle_readiness,
            "/health/providers": self._handle_providers,
        }
        if route_path == "/metrics":
            await self._send_text_response(
                writer,
                200,
                self._handle_metrics(),
                content_type=_PROMETHEUS_TEXT_CONTENT_TYPE,
            )
            return
        handler = handlers.get(route_path)
        if handler:
            response = await handler()
            await self._send_json_response(writer, response)
            return
        if route_path.startswith("/ops/quarantine/"):
            await dispatch_quarantine_request(
                self,
                writer=writer,
                path=route_path,
                query=query,
            )
            return
        if route_path.startswith("/ops/control-plane/"):
            await dispatch_control_plane_request(
                self,
                writer=writer,
                path=route_path,
                query=query,
            )
            return
        if route_path.startswith("/ops/observability/"):
            await dispatch_observability_request(
                self,
                writer=writer,
                path=route_path,
                query=query,
            )
            return
        await self._send_response(writer, 404, _NOT_FOUND_MESSAGE)

    def _parse_query_params(self, raw_query: str) -> dict[str, str]:
        """Parse query string into a single-value key/value mapping."""
        parsed = parse_qs(raw_query, keep_blank_values=False)
        return {key: values[-1] for key, values in parsed.items() if values}

    def _read_required_param(
        self,
        query: dict[str, str],
        name: str,
    ) -> str:
        """Return required query parameter or raise ValueError."""
        value = query.get(name)
        if value is None or not value.strip():
            raise ValueError(f"Missing required query parameter: {name}")
        return value.strip()

    @staticmethod
    def _read_optional_param(query: dict[str, str], name: str) -> str | None:
        """Return an optional query parameter as stripped value."""
        value = query.get(name)
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _is_all_scope_token(value: str | None) -> bool:
        """Return True when a selector token represents Grafana's All scope."""
        if value is None:
            return False
        normalized = value.strip()
        return normalized in {"All", "$__all", "__all", "*"}

    def _read_optional_scope_param(
        self,
        query: dict[str, str],
        name: str,
    ) -> str | None:
        """Return optional scope value, normalizing Grafana All to no filter."""
        value = self._read_optional_param(query, name)
        if self._is_all_scope_token(value):
            return None
        return value

    def _read_int_param(
        self,
        query: dict[str, str],
        name: str,
        default: int,
        *,
        minimum: int,
    ) -> int:
        """Parse one integer query parameter with bounds validation."""
        raw = self._read_optional_param(query, name)
        if raw is None:
            return default
        parsed = int(raw)
        if parsed < minimum:
            raise ValueError(f"Invalid query parameter: {name} must be >= {minimum}")
        return parsed

    @staticmethod
    def _read_csv_param(query: dict[str, str], name: str) -> tuple[str, ...]:
        """Parse a CSV-style optional query parameter into unique ordered tokens."""
        raw = HealthServerRoutingMixin._read_optional_param(query, name)
        if raw is None:
            return ()
        normalized_raw = raw.strip()
        if normalized_raw.startswith("{") and normalized_raw.endswith("}"):
            normalized_raw = normalized_raw[1:-1]
        items: list[str] = []
        for part in normalized_raw.split(","):
            normalized = part.strip()
            if normalized and normalized not in items:
                items.append(normalized)
        return tuple(items)

    @classmethod
    def _read_scope_csv_param(cls, query: dict[str, str], name: str) -> tuple[str, ...]:
        """Parse CSV scope values, collapsing Grafana All to an unbounded filter."""
        items = cls._read_csv_param(query, name)
        if any(cls._is_all_scope_token(item) for item in items):
            return ()
        return items

    async def _handle_health(self) -> HealthResponse:
        """Handle /health endpoint - overall health status."""
        await asyncio.sleep(0)
        status = self._get_overall_status()
        checks: JsonDict = {  # Any: response payload values are heterogeneous
            "server": {
                "status": "healthy",
                "uptime_seconds": round(self.uptime_seconds, 2),
            }
        }
        if self._health_monitor:
            checks["providers"] = self._get_provider_statuses()
        return HealthResponse(
            status=status.value.lower(),
            timestamp=self._response_timestamp(),
            checks=checks,
        )

    async def _handle_liveness(self) -> HealthResponse:
        """Handle /health/live endpoint."""
        await asyncio.sleep(0)
        return HealthResponse(
            status="healthy",
            timestamp=self._response_timestamp(),
            checks={
                "server": {
                    "status": "healthy",
                    "uptime_seconds": round(self.uptime_seconds, 2),
                }
            },
        )

    async def _handle_readiness(self) -> HealthResponse:
        """Handle /health/ready endpoint."""
        await asyncio.sleep(0)
        if not self._health_monitor:
            return HealthResponse(
                status="healthy",
                timestamp=self._response_timestamp(),
                checks={"message": "No health monitor configured"},
            )
        provider_statuses = self._get_provider_statuses()
        has_unhealthy = any(
            status.get("status") == "unhealthy" for status in provider_statuses.values()
        )
        status = "unhealthy" if has_unhealthy else "healthy"
        return HealthResponse(
            status=status,
            timestamp=self._response_timestamp(),
            checks={"providers": provider_statuses},
        )

    async def _handle_providers(self) -> HealthResponse:
        """Handle /health/providers endpoint."""
        await asyncio.sleep(0)
        if not self._health_monitor:
            return HealthResponse(
                status="healthy",
                timestamp=self._response_timestamp(),
                checks={"message": "No health monitor configured"},
            )
        return HealthResponse(
            status=self._get_overall_status().value.lower(),
            timestamp=self._response_timestamp(),
            checks={"providers": self._get_provider_statuses()},
        )

    def _handle_metrics(self) -> str:
        """Return minimal Prometheus exposition for scrape liveness.

        Prometheus derives the bounded availability signal from
        up{job="quarantine-explorer"} after a successful scrape. This endpoint
        intentionally avoids record-level or run-level labels.
        """
        return "# BioETL health server scrape endpoint\n"


__all__ = ["HealthServerRoutingMixin"]
