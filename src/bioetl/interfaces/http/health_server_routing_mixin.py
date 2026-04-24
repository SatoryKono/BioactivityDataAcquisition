"""Routing and endpoint handlers for HealthServer."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Protocol, cast
from urllib.parse import parse_qs, unquote, urlsplit

from bioetl.domain.context import current_utc_time
from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.interfaces.http.types import HealthResponse

if TYPE_CHECKING:
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.domain.ports import ClockPort, HealthMonitorPort

_NOT_FOUND_MESSAGE = "Not Found"


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

    async def _send_payload_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        payload: dict[str, object],
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
    _quarantine_service: QuarantineService | None
    _clock: ClockPort | None

    @property
    def uptime_seconds(self) -> float:
        """Get server uptime in seconds."""
        raise NotImplementedError

    def _response_timestamp(self) -> str:
        """Return the sanctioned timestamp source for health responses."""
        clock = getattr(self, "_clock", None)
        if clock is not None:
            return clock.now().isoformat()
        return current_utc_time().isoformat()

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
        handler = handlers.get(route_path)
        if handler:
            response = await handler()
            response_support = cast(_HealthResponseSupport, self)
            await response_support._send_json_response(writer, response)
            return
        if route_path.startswith("/ops/quarantine/"):
            await self._route_quarantine_request(
                writer=writer,
                path=route_path,
                query=query,
            )
            return
        response_support = cast(_HealthResponseSupport, self)
        await response_support._send_response(writer, 404, _NOT_FOUND_MESSAGE)

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

    async def _route_quarantine_request(
        self,
        *,
        writer: asyncio.StreamWriter,
        path: str,
        query: dict[str, str],
    ) -> None:
        """Route record-level quarantine explorer requests."""
        response_support = cast(_HealthResponseSupport, self)
        if self._quarantine_service is None:
            await response_support._send_response(
                writer,
                503,
                "Quarantine explorer unavailable",
            )
            return

        try:
            if path == "/ops/quarantine/filtered-records":
                await self._handle_filtered_records(writer, query)
                return
            if path == "/ops/quarantine/filtered-stats":
                await self._handle_filtered_stats(writer, query)
                return
            if path == "/ops/quarantine/filter-options":
                await self._handle_filter_options(writer, query)
                return
            if path.startswith("/ops/quarantine/filtered-record/"):
                payload_hash = unquote(path.rsplit("/", maxsplit=1)[-1]).strip()
                if not payload_hash:
                    raise ValueError("Missing payload_hash in path")
                await self._handle_filtered_record_detail(writer, query, payload_hash)
                return
            await response_support._send_response(writer, 404, _NOT_FOUND_MESSAGE)
        except ValueError as exc:
            await response_support._send_response(writer, 400, str(exc))

    async def _handle_filtered_records(
        self,
        writer: asyncio.StreamWriter,
        query: dict[str, str],
    ) -> None:
        """Handle paginated list endpoint for filtered Silver records."""
        assert self._quarantine_service is not None
        pipeline = self._read_required_param(query, "pipeline")
        limit = self._read_int_param(query, "limit", default=50, minimum=1)
        offset = self._read_int_param(query, "offset", default=0, minimum=0)
        payload = await self._quarantine_service.list_filtered_records(
            pipeline=pipeline,
            run_type=self._read_optional_param(query, "run_type"),
            reason_code=self._read_optional_param(query, "reason_code"),
            field=self._read_optional_param(query, "field"),
            run_id=self._read_optional_param(query, "run_id"),
            payload_hash=self._read_optional_param(query, "payload_hash"),
            from_ts=self._read_optional_param(query, "from"),
            to_ts=self._read_optional_param(query, "to"),
            limit=limit,
            offset=offset,
            sort=self._read_optional_param(query, "sort") or "ingestion_ts_desc",
        )
        response_support = cast(_HealthResponseSupport, self)
        await response_support._send_payload_response(writer, 200, payload)

    async def _handle_filtered_stats(
        self,
        writer: asyncio.StreamWriter,
        query: dict[str, str],
    ) -> None:
        """Handle aggregate stats endpoint for filtered Silver records."""
        assert self._quarantine_service is not None
        pipeline = self._read_required_param(query, "pipeline")
        payload = await self._quarantine_service.get_filtered_stats(
            pipeline=pipeline,
            run_type=self._read_optional_param(query, "run_type"),
            reason_code=self._read_optional_param(query, "reason_code"),
            field=self._read_optional_param(query, "field"),
            run_id=self._read_optional_param(query, "run_id"),
            payload_hash=self._read_optional_param(query, "payload_hash"),
            from_ts=self._read_optional_param(query, "from"),
            to_ts=self._read_optional_param(query, "to"),
        )
        response_support = cast(_HealthResponseSupport, self)
        await response_support._send_payload_response(writer, 200, payload)

    async def _handle_filter_options(
        self,
        writer: asyncio.StreamWriter,
        query: dict[str, str],
    ) -> None:
        """Handle variable-options endpoint for filtered Silver records."""
        assert self._quarantine_service is not None
        pipeline = self._read_required_param(query, "pipeline")
        payload = await self._quarantine_service.get_filtered_filter_options(
            pipeline=pipeline,
            run_type=self._read_optional_param(query, "run_type"),
            reason_code=self._read_optional_param(query, "reason_code"),
            field=self._read_optional_param(query, "field"),
            run_id=self._read_optional_param(query, "run_id"),
            from_ts=self._read_optional_param(query, "from"),
            to_ts=self._read_optional_param(query, "to"),
        )
        response_support = cast(_HealthResponseSupport, self)
        await response_support._send_payload_response(writer, 200, payload)

    async def _handle_filtered_record_detail(
        self,
        writer: asyncio.StreamWriter,
        query: dict[str, str],
        payload_hash: str,
    ) -> None:
        """Handle detail endpoint for one filtered Silver record."""
        assert self._quarantine_service is not None
        payload = await self._quarantine_service.get_filtered_record(
            payload_hash=payload_hash,
            pipeline=self._read_required_param(query, "pipeline"),
        )
        response_support = cast(_HealthResponseSupport, self)
        if payload is None:
            await response_support._send_response(writer, 404, _NOT_FOUND_MESSAGE)
            return
        await response_support._send_payload_response(writer, 200, payload)

    async def _handle_health(self) -> HealthResponse:
        """Handle /health endpoint - overall health status."""
        await asyncio.sleep(0)
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
        state_support = cast(_HealthStateSupport, self)
        provider_statuses = state_support._get_provider_statuses()
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
        state_support = cast(_HealthStateSupport, self)
        return HealthResponse(
            status=state_support._get_overall_status().value.lower(),
            timestamp=self._response_timestamp(),
            checks={"providers": state_support._get_provider_statuses()},
        )


__all__ = ["HealthServerRoutingMixin"]
