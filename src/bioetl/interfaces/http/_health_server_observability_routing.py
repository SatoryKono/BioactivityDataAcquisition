"""Observability helper routing for HealthServer."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Protocol

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.types import RunID
from bioetl.interfaces.http._forensic_request_budget import (
    ForensicEndpointUnavailable,
    forensic_unavailable_payload,
    run_bounded_forensic_operation,
)
from bioetl.interfaces.http.processed_records_table import (
    build_processed_records_table_payload_from_ledger,
    build_processed_records_table_payload_from_prometheus,
    read_processed_records_run_id,
)
from bioetl.interfaces.http.run_report_ops import (
    list_pipeline_run_report_payloads,
    list_workflow_run_report_payloads,
    load_pipeline_run_report_payload,
    load_workflow_run_report_payload,
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
    @property
    def _forensic_endpoint_limiter(self) -> asyncio.Semaphore: ...

    @property
    def _prometheus_base_url(self) -> str: ...

    @property
    def _run_ledger_port(self) -> _RunLedgerLookup | None: ...

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
    try:
        if path == "/ops/observability/processed-records":
            await handle_processed_records_table(host, writer, query)
            return
        if path == "/ops/observability/pipeline-run-report":
            await handle_pipeline_run_report(host, writer, query)
            return
        if path == "/ops/observability/workflow-run-report":
            await handle_workflow_run_report(host, writer, query)
            return
        if path == "/ops/observability/pipeline-run-reports":
            await handle_pipeline_run_reports_list(host, writer, query)
            return
        if path == "/ops/observability/workflow-run-reports":
            await handle_workflow_run_reports_list(host, writer, query)
            return
        await host._send_response(writer, 404, _NOT_FOUND_MESSAGE)
    except ValueError as exc:
        await host._send_response(writer, 400, str(exc))
    except RuntimeError as exc:
        await host._send_response(writer, 502, str(exc))


async def handle_pipeline_run_report(
    host: _HealthObservabilityRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Serve stored pipeline_run_report_v1 JSON for a completed run."""
    run_id = host._read_required_param(query, "run_id")
    pipeline = host._read_required_param(query, "pipeline")
    try:
        payload = await run_bounded_forensic_operation(
            limiter=host._forensic_endpoint_limiter,
            operation_factory=lambda: asyncio.to_thread(
                load_pipeline_run_report_payload,
                run_id=run_id,
                pipeline_name=pipeline,
            ),
        )
    except ForensicEndpointUnavailable as exc:
        await host._send_payload_response(
            writer,
            503,
            forensic_unavailable_payload(exc),
        )
        return
    if payload is None:
        await host._send_payload_response(
            writer,
            404,
            {
                "status": "not_found",
                "message": "pipeline run report not found",
                "run_id": run_id,
                "pipeline": pipeline,
            },
        )
        return
    await host._send_payload_response(writer, 200, payload)


async def handle_workflow_run_report(
    host: _HealthObservabilityRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Serve stored workflow_run_report_v1 JSON for a completed workflow run."""
    workflow_run_id = host._read_required_param(query, "workflow_run_id")
    workflow_name = host._read_required_param(query, "workflow")
    try:
        payload = await run_bounded_forensic_operation(
            limiter=host._forensic_endpoint_limiter,
            operation_factory=lambda: asyncio.to_thread(
                load_workflow_run_report_payload,
                workflow_run_id=workflow_run_id,
                workflow_name=workflow_name,
            ),
        )
    except ForensicEndpointUnavailable as exc:
        await host._send_payload_response(
            writer,
            503,
            forensic_unavailable_payload(exc),
        )
        return
    if payload is None:
        await host._send_payload_response(
            writer,
            404,
            {
                "status": "not_found",
                "message": "workflow run report not found",
                "workflow_run_id": workflow_run_id,
                "workflow": workflow_name,
            },
        )
        return
    await host._send_payload_response(writer, 200, payload)


async def handle_pipeline_run_reports_list(
    host: _HealthObservabilityRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """List recent pipeline run reports for a pipeline (or all)."""
    pipeline = host._read_optional_param(query, "pipeline")
    limit_raw = host._read_optional_param(query, "limit") or "20"
    try:
        limit = max(1, min(100, int(limit_raw)))
    except ValueError as exc:
        raise ValueError("limit must be an integer") from exc
    try:
        payload = await run_bounded_forensic_operation(
            limiter=host._forensic_endpoint_limiter,
            operation_factory=lambda: asyncio.to_thread(
                list_pipeline_run_report_payloads,
                pipeline_name=pipeline,
                limit=limit,
            ),
        )
    except ForensicEndpointUnavailable as exc:
        await host._send_payload_response(
            writer,
            503,
            forensic_unavailable_payload(exc),
        )
        return
    await host._send_payload_response(writer, 200, payload)


async def handle_workflow_run_reports_list(
    host: _HealthObservabilityRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """List recent workflow run reports for a workflow (or all)."""
    workflow = host._read_optional_param(query, "workflow")
    limit_raw = host._read_optional_param(query, "limit") or "20"
    try:
        limit = max(1, min(100, int(limit_raw)))
    except ValueError as exc:
        raise ValueError("limit must be an integer") from exc
    try:
        payload = await run_bounded_forensic_operation(
            limiter=host._forensic_endpoint_limiter,
            operation_factory=lambda: asyncio.to_thread(
                list_workflow_run_report_payloads,
                workflow_name=workflow,
                limit=limit,
            ),
        )
    except ForensicEndpointUnavailable as exc:
        await host._send_payload_response(
            writer,
            503,
            forensic_unavailable_payload(exc),
        )
        return
    await host._send_payload_response(writer, 200, payload)


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
    operation: Callable[[], dict[str, object]]
    if selected_run_id is not None and host._run_ledger_port is not None:

        def build_from_ledger() -> dict[str, object]:
            return build_processed_records_table_payload_from_ledger(
                ledger_entries=tuple(
                    host._run_ledger_port.list_entries_by_run_id(selected_run_id)
                ),
                pipeline=pipeline,
                run_type=run_type,
            )

        operation = build_from_ledger
    else:

        def build_from_prometheus() -> dict[str, object]:
            return build_processed_records_table_payload_from_prometheus(
                prometheus_base_url=host._prometheus_base_url,
                pipeline=pipeline,
                run_type=run_type,
            )

        operation = build_from_prometheus

    try:
        payload = await run_bounded_forensic_operation(
            limiter=host._forensic_endpoint_limiter,
            operation_factory=lambda: asyncio.to_thread(operation),
        )
    except ForensicEndpointUnavailable as exc:
        await host._send_payload_response(
            writer,
            exc.status_code,
            forensic_unavailable_payload(
                endpoint="processed-records",
                reason=exc.reason,
            ),
        )
        return
    except (ConnectionError, OSError, RuntimeError):
        await host._send_payload_response(
            writer,
            503,
            forensic_unavailable_payload(
                endpoint="processed-records",
                reason="backend_unavailable",
            ),
        )
        return

    await host._send_payload_response(writer, 200, payload)
