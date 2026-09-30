"""Processed Records table endpoint for HealthServer observability routing."""

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
from bioetl.interfaces.http.processed_records_table import (
    build_processed_records_table_payload_from_ledger,
    build_processed_records_table_payload_from_prometheus,
    read_processed_records_run_id,
)

__all__ = ["handle_processed_records_table"]


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
