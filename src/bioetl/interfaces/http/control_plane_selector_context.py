"""Control-plane selector resolution helpers for Grafana dashboard variables."""

from __future__ import annotations

from bioetl.domain.control_plane import RunManifest
from bioetl.interfaces.http._control_plane_selector_filters import (
    filter_records,
    latest_record,
)
from bioetl.interfaces.http._control_plane_selector_payloads import (
    RUN_ID_NO_SELECTION,
    SELECTOR_CONTEXT_CONTRACT,
    UNKNOWN_SCOPE,
    exact_run_only_fallback_values,
    options_payload,
    resolved_via,
    selected_payload,
)
from bioetl.interfaces.http._control_plane_selector_records import (
    RunLedgerLookup,
    build_selector_records,
    narrow_manifest_catalog,
    selected_pipeline_scope,
)

__all__ = (
    "RUN_ID_NO_SELECTION",
    "SELECTOR_CONTEXT_CONTRACT",
    "UNKNOWN_SCOPE",
    "build_selector_context_payload",
    "build_selector_filter_options_payload",
)


def build_selector_context_payload(
    *,
    manifests: tuple[RunManifest, ...],
    ledger_port: RunLedgerLookup | None,
    selected_workflows: tuple[str, ...] = (),
    selected_pipelines: tuple[str, ...] = (),
    selected_run_types: tuple[str, ...] = (),
    selected_run_statuses: tuple[str, ...] = (),
    selected_run_id: str | None = None,
) -> dict[str, object]:
    """Resolve a coherent dashboard selector tuple from local control-plane data."""
    records = build_selector_records(
        narrow_manifest_catalog(
            manifests,
            selected_workflows=selected_workflows,
            selected_pipelines=selected_pipelines,
            selected_run_types=selected_run_types,
            selected_run_id=selected_run_id,
        ),
        ledger_port,
    )
    candidates = filter_records(
        records,
        selected_workflows=selected_workflows,
        selected_pipelines=selected_pipelines,
        selected_run_types=selected_run_types,
        selected_run_statuses=selected_run_statuses,
        selected_run_id=selected_run_id,
    )
    selected = latest_record(candidates)
    return {
        "contract": SELECTOR_CONTEXT_CONTRACT,
        "resolved_via": resolved_via(selected, selected_run_id),
        "selected": selected_payload(selected),
        "options": options_payload(candidates if candidates else records),
    }


def build_selector_filter_options_payload(
    *,
    manifests: tuple[RunManifest, ...],
    ledger_port: RunLedgerLookup | None,
    dimension: str,
    response_shape: str,
    requested_pipeline: str | None,
    selected_workflows: tuple[str, ...] = (),
    selected_pipelines: tuple[str, ...] = (),
    selected_run_types: tuple[str, ...] = (),
    selected_run_statuses: tuple[str, ...] = (),
    selected_run_id: str | None = None,
    exact_run_only: bool = False,
    fallback_value: str | None = None,
) -> dict[str, object]:
    """Build Grafana variable option responses from the selector catalog."""
    records = build_selector_records(
        narrow_manifest_catalog(
            manifests,
            selected_workflows=selected_workflows,
            selected_pipelines=selected_pipeline_scope(
                selected_pipelines, requested_pipeline
            ),
            selected_run_types=selected_run_types,
            selected_run_id=selected_run_id,
            fail_open_when_empty=False,
        ),
        ledger_port,
    )
    candidates = filter_records(
        records,
        selected_workflows=selected_workflows,
        selected_pipelines=selected_pipelines,
        selected_run_types=selected_run_types,
        selected_run_statuses=selected_run_statuses,
        selected_run_id=selected_run_id,
    )
    option_records = candidates if candidates else records
    options = options_payload(option_records)
    if dimension not in options:
        raise ValueError(f"Unsupported control-plane filter dimension: {dimension}")
    values = list(options[dimension])
    if exact_run_only and (selected_run_id is None or not values):
        values = exact_run_only_fallback_values(fallback_value)
    if dimension == "run_id":
        values = [RUN_ID_NO_SELECTION, *[value for value in values if value]]
    if response_shape == "list":
        return {"items": values}
    return {
        "contract": SELECTOR_CONTEXT_CONTRACT,
        "dimension": dimension,
        "pipeline": requested_pipeline,
        "run_type": list(selected_run_types),
        "items": values,
    }
