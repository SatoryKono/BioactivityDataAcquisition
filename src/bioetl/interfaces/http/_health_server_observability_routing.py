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
from bioetl.interfaces.http._pipeline_run_report_table import (
    _is_unresolved_run_scope,
    _not_found_pipeline_run_report_shell,
    _table_shape_pipeline_run_report,
    _unresolved_pipeline_run_report_shell,
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

# Re-export table-shell helpers for existing unit imports.
__all__ = (
    "_is_unresolved_run_scope",
    "_not_found_pipeline_run_report_shell",
    "_table_shape_pipeline_run_report",
    "_unresolved_pipeline_run_report_shell",
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
    if _is_unresolved_run_scope(run_id):
        # Default Grafana run_id is "-" — return empty shell (HTTP 200) so
        # Run Explorer detail tables show No data, not QUERY_ERROR/404.
        await host._send_payload_response(
            writer,
            200,
            _unresolved_pipeline_run_report_shell(run_id=run_id, pipeline=pipeline),
        )
        return
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
            exc.status_code,
            forensic_unavailable_payload(
                endpoint="pipeline-run-report",
                reason=exc.reason,
            ),
        )
        return
    if payload is None:
        # Prefer HTTP 200 empty shell over 404 so Grafana tables show No data
        # instead of QUERY_ERROR (#7650).
        await host._send_payload_response(
            writer,
            200,
            _not_found_pipeline_run_report_shell(run_id=run_id, pipeline=pipeline),
        )
        return
    await host._send_payload_response(
        writer,
        200,
        _table_shape_pipeline_run_report(payload),
    )


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
            exc.status_code,
            forensic_unavailable_payload(
                endpoint="workflow-run-report",
                reason=exc.reason,
            ),
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
    """List recent pipeline run reports for a pipeline (or all).

    Index listing is intentionally outside the forensic budget: Browse Recent
    Runs must stay responsive even when retention/detail forensic slots are busy.
    """
    pipeline = host._read_optional_param(query, "pipeline")
    limit_raw = host._read_optional_param(query, "limit") or "20"
    try:
        limit = max(1, min(100, int(limit_raw)))
    except ValueError as exc:
        raise ValueError("limit must be an integer") from exc
    payload = await asyncio.to_thread(
        list_pipeline_run_report_payloads,
        pipeline_name=pipeline,
        limit=limit,
    )
    await host._send_payload_response(writer, 200, payload)


async def handle_workflow_run_reports_list(
    host: _HealthObservabilityRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """List recent workflow run reports for a workflow (or all).

    Same as pipeline list: keep index listing off the forensic semaphore.
    """
    workflow = host._read_optional_param(query, "workflow")
    limit_raw = host._read_optional_param(query, "limit") or "20"
    try:
        limit = max(1, min(100, int(limit_raw)))
    except ValueError as exc:
        raise ValueError("limit must be an integer") from exc
    payload = await asyncio.to_thread(
        list_workflow_run_report_payloads,
        workflow_name=workflow,
        limit=limit,
    )
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
    run_ledger = host._run_ledger_port
    if selected_run_id is None:

        def build_selection_required() -> dict[str, object]:
            return {
                "contract": "processed_records_table_v1",
                "pipeline": pipeline,
                "run_type": [part for part in (run_type or "").split(",") if part.strip()],
                "selection": "required",
                "rows": [],
            }

        operation = build_selection_required
    elif run_ledger is not None:

        def build_from_ledger() -> dict[str, object]:
            return build_processed_records_table_payload_from_ledger(
                ledger_entries=tuple(
                    run_ledger.list_entries_by_run_id(selected_run_id)
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
