"""Observability helper routing for HealthServer."""

from __future__ import annotations

import asyncio
from typing import Protocol, cast

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.types import RunID
from bioetl.interfaces.http.processed_records_table import (
    build_processed_records_table_payload_from_ledger,
    build_processed_records_table_payload_from_prometheus,
    read_processed_records_run_id,
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


class _HealthObservabilityRoutingHost(_HealthResponseSupport, Protocol):
    _prometheus_base_url: str
    _run_ledger_port: _RunLedgerLookup | None

    def _read_required_param(self, query: dict[str, str], name: str) -> str: ...

    @staticmethod
    def _read_optional_param(query: dict[str, str], name: str) -> str | None: ...


class _RunLedgerLookup(Protocol):
    def list_entries_by_run_id(self, run_id: RunID) -> list[RunLedgerEntry]: ...


async def dispatch_observability_request(
    host: _HealthObservabilityRoutingHost,
    *,
    writer: asyncio.StreamWriter,
    path: str,
    query: dict[str, str],
) -> None:
    """Route dashboard observability helper endpoints."""
    response_support = cast(_HealthResponseSupport, host)
    try:
        if path == "/ops/observability/processed-records":
            await handle_processed_records_table(host, writer, query)
            return
        await response_support._send_response(writer, 404, _NOT_FOUND_MESSAGE)
    except ValueError as exc:
        await response_support._send_response(writer, 400, str(exc))
    except RuntimeError as exc:
        await response_support._send_response(writer, 502, str(exc))


async def handle_processed_records_table(
    host: _HealthObservabilityRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Handle formatted Processed Records table rows for Grafana."""
    pipeline = host._read_required_param(query, "pipeline")
    run_type = host._read_optional_param(query, "run_type")
    selected_run_id = read_processed_records_run_id(
        host._read_optional_param(query, "run_id")
    )
    if selected_run_id is not None and host._run_ledger_port is not None:
        payload = build_processed_records_table_payload_from_ledger(
            ledger_entries=tuple(
                host._run_ledger_port.list_entries_by_run_id(selected_run_id)
            ),
            pipeline=pipeline,
            run_type=run_type,
        )
        await host._send_payload_response(writer, 200, payload)
        return

    payload = await asyncio.to_thread(
        build_processed_records_table_payload_from_prometheus,
        prometheus_base_url=host._prometheus_base_url,
        pipeline=pipeline,
        run_type=run_type,
    )
    await host._send_payload_response(writer, 200, payload)
