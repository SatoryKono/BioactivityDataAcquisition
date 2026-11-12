"""Processed Records table endpoint for HealthServer observability routing."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from bioetl.application.services.evidence_location.resolver import (
    EvidenceLocationResolver,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.types import RunID
from bioetl.interfaces.http._forensic_request_budget import (
    ForensicEndpointUnavailable,
    forensic_unavailable_payload,
    run_bounded_forensic_operation,
)
from bioetl.interfaces.http._health_server_observability_protocols import (
    _HealthObservabilityRoutingHost,
)
from bioetl.interfaces.http._processed_records_value_support import _selector_tokens
from bioetl.interfaces.http.processed_records_table import (
    build_processed_records_table_payload_from_ledger,
    build_processed_records_table_payload_from_prometheus,
    read_processed_records_run_id,
)
from bioetl.interfaces.http.run_report_ops import load_pipeline_run_report_payload

__all__ = ["handle_processed_records_table"]


def _selected_ledger_entries(
    host: _HealthObservabilityRoutingHost,
    *,
    pipeline: str,
    run_id: RunID,
    run_type: str | None,
) -> tuple[RunLedgerEntry, ...]:
    """Use the same identity-bound evidence root as the other run details."""
    resolver = getattr(host, "_evidence_location_resolver", None)
    if not isinstance(resolver, EvidenceLocationResolver):
        ledger = host._run_ledger_port
        return tuple(ledger.list_entries_by_run_id(run_id)) if ledger else ()
    resolved = resolver.resolve(
        kind="pipeline",
        owner=pipeline,
        run_id=str(run_id),
        expected_runtime_source_id=getattr(host, "_runtime_source_id", None),
    )
    if resolved.context is None or resolved.code.value in {
        "identity_conflict",
        "location_invalid",
    }:
        raise ForensicEndpointUnavailable(reason=resolved.code.value, status_code=409)
    manifest = resolved.context.get_manifest_by_run_id(run_id)
    if manifest is None:
        raise ForensicEndpointUnavailable(reason="manifest_missing", status_code=404)
    requested_types = _selector_tokens(run_type)
    if (
        not isinstance(manifest, RunManifest)
        or str(manifest.run_id) != str(run_id)
        or manifest.pipeline_name != pipeline
        or (requested_types and manifest.run_type.value not in requested_types)
    ):
        raise ForensicEndpointUnavailable(
            reason="selector_context_mismatch", status_code=409
        )
    entries = resolved.context.get_ledger_entries_by_run_id(run_id)
    if any(str(entry.run_id) != str(run_id) for entry in entries):
        raise ForensicEndpointUnavailable(
            reason="ledger_identity_conflict", status_code=409
        )
    return entries


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
    elif run_ledger is not None or isinstance(
        getattr(host, "_evidence_location_resolver", None), EvidenceLocationResolver
    ):

        def build_from_ledger() -> dict[str, object]:
            # Empty ledger entries stay UNKNOWN (DASH-STATE-001). Prometheus
            # current metrics are pipeline/run_type aggregates and MUST NOT
            # be presented as the selected UUID (DASH-SCOPE-001 / DASH-DATA-002).
            ledger_entries = _selected_ledger_entries(
                host, pipeline=pipeline, run_id=selected_run_id, run_type=run_type
            )
            # Saved-report fill is unused when the ledger is empty — skip I/O.
            report = (
                load_pipeline_run_report_payload(
                    pipeline_name=pipeline,
                    run_id=str(selected_run_id),
                )
                if ledger_entries
                else None
            )
            return build_processed_records_table_payload_from_ledger(
                ledger_entries=ledger_entries,
                pipeline=pipeline,
                run_type=run_type,
                report=report,
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
    except (BioETLError, OSError, RuntimeError, ValueError):
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
