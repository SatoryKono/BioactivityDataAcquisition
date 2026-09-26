"""Observability helper routing for HealthServer."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from bioetl.interfaces.http._forensic_request_budget import (
    ForensicEndpointUnavailable,
    forensic_unavailable_payload,
    run_bounded_forensic_operation,
)
from bioetl.interfaces.http._health_server_observability_protocols import (
    _HealthObservabilityRoutingHost,
)
from bioetl.interfaces.http._pipeline_run_report_sections import (
    _is_unresolved_run_scope,
)
from bioetl.interfaces.http._pipeline_run_report_table import (
    _not_found_pipeline_run_report_shell,
    _summary_rows_pipeline_run_report,
    _table_shape_pipeline_run_report,
    _table_shape_workflow_run_report,
    _unresolved_pipeline_run_report_shell,
)
from bioetl.interfaces.http._run_explorer_snapshot import (
    take_default_recent_snapshot,
)
from bioetl.interfaces.http.processed_records_table import (
    build_processed_records_table_payload_from_ledger,
    build_processed_records_table_payload_from_prometheus,
    read_processed_records_run_id,
)
from bioetl.interfaces.http.recent_pipeline_runs import (
    _report_link,
    list_recent_pipeline_runs,
)
from bioetl.interfaces.http.run_report_ops import (
    list_pipeline_run_report_payloads,
    list_workflow_run_report_payloads,
    load_pipeline_run_report_artifact,
    load_pipeline_run_report_payload,
    load_workflow_run_report_payload,
)
from bioetl.interfaces.http.selected_run_status import handle_selected_run_status

# Re-export table-shell helpers for existing unit imports.
__all__ = (
    "_is_unresolved_run_scope",
    "_not_found_pipeline_run_report_shell",
    "_summary_rows_pipeline_run_report",
    "_table_shape_pipeline_run_report",
    "_table_shape_workflow_run_report",
    "_unresolved_pipeline_run_report_shell",
)

_NOT_FOUND_MESSAGE = "Not Found"


async def dispatch_observability_request(
    host: _HealthObservabilityRoutingHost,
    *,
    writer: asyncio.StreamWriter,
    path: str,
    query: dict[str, str],
) -> None:
    """Route dashboard observability helper endpoints."""
    try:
        if path == "/ops/observability/selected-run-status":
            await handle_selected_run_status(host, writer, query)
            return
        if path == "/ops/observability/processed-records":
            await handle_processed_records_table(host, writer, query)
            return
        if path == "/ops/observability/pipeline-run-report":
            await handle_pipeline_run_report(host, writer, query)
            return
        if path == "/ops/observability/pipeline-run-report-artifact":
            await handle_pipeline_run_report_artifact(host, writer, query)
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


async def handle_pipeline_run_report_artifact(
    host: _HealthObservabilityRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Open an exact persisted artifact with explicit missing/error responses."""
    pipeline = host._read_required_param(query, "pipeline")
    run_id = host._read_required_param(query, "run_id")
    artifact_format = host._read_required_param(query, "format")
    try:
        body = await run_bounded_forensic_operation(
            limiter=host._forensic_endpoint_limiter,
            operation_factory=lambda: asyncio.to_thread(
                load_pipeline_run_report_artifact,
                pipeline=pipeline,
                run_id=run_id,
                artifact_format=artifact_format,
            ),
        )
    except ForensicEndpointUnavailable as exc:
        await host._send_payload_response(
            writer,
            exc.status_code,
            forensic_unavailable_payload(
                endpoint="pipeline-run-report-artifact", reason=exc.reason
            ),
        )
        return
    if body is None:
        await host._send_text_response(
            writer,
            404,
            "Report not found / Отчёт отсутствует\n\n"
            "The report may not have been generated yet or may have been removed.\n"
            "Refresh Run Explorer to check availability.\n",
            content_type="text/plain; charset=utf-8",
        )
        return
    content_type = (
        "application/json; charset=utf-8"
        if artifact_format == "pipeline_run_report_json"
        else "text/plain; charset=utf-8"
    )
    await host._send_text_response(writer, 200, body, content_type=content_type)


async def handle_pipeline_run_report(
    host: _HealthObservabilityRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Serve stored pipeline_run_report_v1 JSON for a completed run."""
    run_id = host._read_required_param(query, "run_id")
    pipeline = host._read_required_param(query, "pipeline")
    view_summary = str(query.get("view") or "").strip().lower() == "summary"

    def _present(payload: dict[str, object]) -> dict[str, object]:
        if view_summary:
            summary = _summary_rows_pipeline_run_report(
                payload,
                grafana_from=query.get("from"),
                grafana_to=query.get("to"),
            )
            if isinstance(payload.get("identity"), dict):
                rows = summary.get("summary")
                if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                    rows[0].update(
                        _report_link(
                            {"pipeline": pipeline, "run_id": run_id, "json_path": True},
                            None,
                        )
                    )
            return summary
        return _table_shape_pipeline_run_report(payload)

    if _is_unresolved_run_scope(run_id):
        # Default Grafana run_id is "-" — return empty shell (HTTP 200) so
        # Run Explorer detail tables show No data, not QUERY_ERROR/404.
        await host._send_payload_response(
            writer,
            200,
            _present(
                _unresolved_pipeline_run_report_shell(run_id=run_id, pipeline=pipeline)
            ),
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
            _present(
                _not_found_pipeline_run_report_shell(run_id=run_id, pipeline=pipeline)
            ),
        )
        return
    await host._send_payload_response(writer, 200, _present(payload))


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
    await host._send_payload_response(
        writer, 200, _table_shape_workflow_run_report(payload)
    )


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
    selected_run_id = host._read_optional_param(query, "run_id")
    limit_raw = host._read_optional_param(query, "limit") or "20"
    try:
        limit = max(1, min(100, int(limit_raw)))
    except ValueError as exc:
        raise ValueError("limit must be an integer") from exc
    if query.get("view") == "recent":
        workflow = host._read_optional_param(query, "workflow")
        run_type = host._read_optional_param(query, "run_type")
        lookup_run_id = host._read_optional_param(query, "lookup_run_id")
        cached = take_default_recent_snapshot(
            getattr(host, "_run_explorer_snapshot", None),
            view=query.get("view"),
            limit=limit,
            pipeline=pipeline,
            workflow=workflow,
            run_type=run_type,
            run_id=selected_run_id,
            lookup_run_id=lookup_run_id,
        )
        if cached is not None:
            await host._send_payload_response(writer, 200, cached)
            return
        payload = await asyncio.to_thread(
            list_recent_pipeline_runs,
            pipeline=pipeline,
            workflow=workflow,
            run_type=run_type,
            selected_run_id=selected_run_id,
            lookup_run_id=lookup_run_id,
            limit=limit,
            manifest_port=host._run_manifest_port,
            ledger_port=host._run_ledger_port,
        )
        await host._send_payload_response(writer, 200, payload)
        return
    payload = await asyncio.to_thread(
        list_pipeline_run_report_payloads,
        pipeline_name=pipeline,
        limit=limit,
        selected_run_id=selected_run_id,
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
                "run_type": [
                    part for part in (run_type or "").split(",") if part.strip()
                ],
                "selection": "required",
                "rows": [],
            }

        operation = build_selection_required
    elif run_ledger is not None:

        def build_from_ledger() -> dict[str, object]:
            # Empty ledger entries stay UNKNOWN (DASH-STATE-001). Prometheus
            # current metrics are pipeline/run_type aggregates and MUST NOT
            # be presented as the selected UUID (DASH-SCOPE-001 / DASH-DATA-002).
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
