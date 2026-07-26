"""Quarantine explorer routing helpers for HealthServer."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Protocol
from urllib.parse import unquote

if TYPE_CHECKING:
    from bioetl.application.services.quarantine_service import QuarantineService

from bioetl.interfaces.http._forensic_request_budget import (
    ForensicEndpointUnavailable,
    forensic_unavailable_payload,
    run_bounded_forensic_operation,
)

_NOT_FOUND_MESSAGE = "Not Found"


class _HealthResponseSupport(Protocol):
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


class _HealthQuarantineRoutingHost(_HealthResponseSupport, Protocol):
    @property
    def _forensic_endpoint_limiter(self) -> asyncio.Semaphore: ...

    @property
    def _quarantine_service(self) -> QuarantineService | None: ...

    def _read_required_param(self, query: dict[str, str], name: str) -> str: ...

    @staticmethod
    def _read_optional_param(query: dict[str, str], name: str) -> str | None: ...

    def _read_int_param(
        self,
        query: dict[str, str],
        name: str,
        default: int,
        *,
        minimum: int,
    ) -> int: ...


async def dispatch_quarantine_request(
    host: _HealthQuarantineRoutingHost,
    *,
    writer: asyncio.StreamWriter,
    path: str,
    query: dict[str, str],
) -> None:
    """Route record-level quarantine explorer requests."""
    if host._quarantine_service is None:
        endpoint = path.rsplit("/", maxsplit=1)[-1] or "quarantine"
        await host._send_payload_response(
            writer,
            503,
            forensic_unavailable_payload(
                endpoint=endpoint,
                reason="backend_unavailable",
            ),
        )
        return

    try:
        if path == "/ops/quarantine/filtered-records":
            await handle_filtered_records(host, writer, query)
            return
        if path == "/ops/quarantine/filtered-stats":
            await handle_filtered_stats(host, writer, query)
            return
        if path == "/ops/quarantine/filtered-timeseries":
            await handle_filtered_timeseries(host, writer, query)
            return
        if path == "/ops/quarantine/filter-options":
            await handle_filter_options(host, writer, query)
            return
        if path.startswith("/ops/quarantine/filtered-record/"):
            payload_hash = unquote(path.rsplit("/", maxsplit=1)[-1]).strip()
            if not payload_hash:
                raise ValueError("Missing payload_hash in path")
            await handle_filtered_record_detail(host, writer, query, payload_hash)
            return
        await host._send_response(writer, 404, _NOT_FOUND_MESSAGE)
    except ValueError as exc:
        await host._send_response(writer, 400, str(exc))


async def handle_filtered_records(
    host: _HealthQuarantineRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle paginated list endpoint for filtered Silver records."""
    assert host._quarantine_service is not None
    pipeline = host._read_required_param(query, "pipeline")
    payload = await host._quarantine_service.list_filtered_records(
        pipeline=pipeline,
        run_type=host._read_optional_param(query, "run_type"),
        reason_code=host._read_optional_param(query, "reason_code"),
        field=host._read_optional_param(query, "field"),
        run_id=host._read_optional_param(query, "run_id"),
        payload_hash=host._read_optional_param(query, "payload_hash"),
        from_ts=host._read_optional_param(query, "from"),
        to_ts=host._read_optional_param(query, "to"),
        limit=host._read_int_param(query, "limit", default=50, minimum=1),
        offset=host._read_int_param(query, "offset", default=0, minimum=0),
        sort=host._read_optional_param(query, "sort") or "ingestion_ts_desc",
    )
    await host._send_payload_response(writer, 200, payload)


async def handle_filtered_stats(
    host: _HealthQuarantineRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle aggregate stats endpoint for filtered Silver records."""
    assert host._quarantine_service is not None
    quarantine_service = host._quarantine_service
    pipeline = host._read_required_param(query, "pipeline")
    try:
        payload = await run_bounded_forensic_operation(
            limiter=host._forensic_endpoint_limiter,
            operation_factory=lambda: quarantine_service.get_filtered_stats(
                pipeline=pipeline,
                run_type=host._read_optional_param(query, "run_type"),
                reason_code=host._read_optional_param(query, "reason_code"),
                field=host._read_optional_param(query, "field"),
                run_id=host._read_optional_param(query, "run_id"),
                payload_hash=host._read_optional_param(query, "payload_hash"),
                from_ts=host._read_optional_param(query, "from"),
                to_ts=host._read_optional_param(query, "to"),
            ),
        )
    except ForensicEndpointUnavailable as exc:
        await host._send_payload_response(
            writer,
            exc.status_code,
            forensic_unavailable_payload(
                endpoint="filtered-stats",
                reason=exc.reason,
            ),
        )
        return
    except (ConnectionError, OSError, RuntimeError):
        await host._send_payload_response(
            writer,
            503,
            forensic_unavailable_payload(
                endpoint="filtered-stats",
                reason="backend_unavailable",
            ),
        )
        return
    await host._send_payload_response(writer, 200, payload)


async def handle_filter_options(
    host: _HealthQuarantineRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle variable-options endpoint for filtered Silver records."""
    assert host._quarantine_service is not None
    pipeline = host._read_required_param(query, "pipeline")
    payload = await host._quarantine_service.get_filtered_filter_options(
        pipeline=pipeline,
        run_type=host._read_optional_param(query, "run_type"),
        reason_code=host._read_optional_param(query, "reason_code"),
        field=host._read_optional_param(query, "field"),
        run_id=host._read_optional_param(query, "run_id"),
        from_ts=host._read_optional_param(query, "from"),
        to_ts=host._read_optional_param(query, "to"),
    )
    await host._send_payload_response(writer, 200, payload)


async def handle_filtered_timeseries(
    host: _HealthQuarantineRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle time-bucketed trend endpoint for filtered Silver records."""
    assert host._quarantine_service is not None
    pipeline = host._read_required_param(query, "pipeline")
    payload = await host._quarantine_service.get_filtered_timeseries(
        pipeline=pipeline,
        run_type=host._read_optional_param(query, "run_type"),
        reason_code=host._read_optional_param(query, "reason_code"),
        field=host._read_optional_param(query, "field"),
        run_id=host._read_optional_param(query, "run_id"),
        payload_hash=host._read_optional_param(query, "payload_hash"),
        from_ts=host._read_optional_param(query, "from"),
        to_ts=host._read_optional_param(query, "to"),
        bucket=host._read_optional_param(query, "bucket") or "1h",
    )
    await host._send_payload_response(writer, 200, payload)


async def handle_filtered_record_detail(
    host: _HealthQuarantineRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
    payload_hash: str,
) -> None:
    """Handle detail endpoint for one filtered Silver record."""
    assert host._quarantine_service is not None
    payload = await host._quarantine_service.get_filtered_record(
        payload_hash=payload_hash,
        pipeline=host._read_required_param(query, "pipeline"),
    )
    if payload is None:
        await host._send_response(writer, 404, _NOT_FOUND_MESSAGE)
        return
    await host._send_payload_response(writer, 200, payload)
