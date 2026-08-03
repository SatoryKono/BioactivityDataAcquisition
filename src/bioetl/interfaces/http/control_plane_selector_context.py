"""Control-plane selector resolution helpers for Grafana dashboard variables."""

from __future__ import annotations

from bioetl.domain.control_plane import RunManifest, WorkflowManifest
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
    build_workflow_aliases,
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
    workflow_manifests: tuple[WorkflowManifest, ...] = (),
) -> dict[str, object]:
    """Resolve a coherent dashboard selector tuple from local control-plane data."""
    workflow_aliases = build_workflow_aliases(workflow_manifests)
    records = build_selector_records(
        narrow_manifest_catalog(
            manifests,
            selected_workflows=selected_workflows,
            selected_pipelines=selected_pipelines,
            selected_run_types=selected_run_types,
            selected_run_id=selected_run_id,
            workflow_aliases=workflow_aliases,
        ),
        ledger_port,
        workflow_aliases=workflow_aliases,
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


def _selector_ledger_for_dimension(
    dimension: str,
    selected_run_statuses: tuple[str, ...],
    ledger_port: RunLedgerLookup | None,
) -> RunLedgerLookup | None:
    if dimension == "run_id" and not selected_run_statuses:
        return None
    return ledger_port


def _apply_exact_run_only_fallback(
    values: list[str],
    *,
    exact_run_only: bool,
    selected_run_id: str | None,
    fallback_value: str | None,
) -> list[str]:
    if exact_run_only and (selected_run_id is None or not values):
        return exact_run_only_fallback_values(fallback_value)
    return values


def _prefix_run_id_no_selection(dimension: str, values: list[str]) -> list[str]:
    if dimension != "run_id":
        return values
    return [RUN_ID_NO_SELECTION, *[value for value in values if value]]


def _dimension_option_values(
    *,
    dimension: str,
    options: dict[str, list[str]],
    exact_run_only: bool,
    selected_run_id: str | None,
    fallback_value: str | None,
) -> list[str]:
    if dimension not in options:
        raise ValueError(f"Unsupported control-plane filter dimension: {dimension}")
    values = list(options[dimension])
    values = _apply_exact_run_only_fallback(
        values,
        exact_run_only=exact_run_only,
        selected_run_id=selected_run_id,
        fallback_value=fallback_value,
    )
    return _prefix_run_id_no_selection(dimension, values)


def _filter_options_response(
    *,
    response_shape: str,
    dimension: str,
    requested_pipeline: str | None,
    selected_run_types: tuple[str, ...],
    values: list[str],
) -> dict[str, object]:
    if response_shape == "list":
        return {"items": values}
    return {
        "contract": SELECTOR_CONTEXT_CONTRACT,
        "dimension": dimension,
        "pipeline": requested_pipeline,
        "run_type": list(selected_run_types),
        "items": values,
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
    workflow_manifests: tuple[WorkflowManifest, ...] = (),
) -> dict[str, object]:
    """Build Grafana variable option responses from the selector catalog."""
    workflow_aliases = build_workflow_aliases(workflow_manifests)
    selector_ledger_port = _selector_ledger_for_dimension(
        dimension,
        selected_run_statuses,
        ledger_port,
    )
    records = build_selector_records(
        narrow_manifest_catalog(
            manifests,
            selected_workflows=selected_workflows,
            selected_pipelines=selected_pipeline_scope(
                selected_pipelines, requested_pipeline
            ),
            selected_run_types=selected_run_types,
            selected_run_id=selected_run_id,
            workflow_aliases=workflow_aliases,
            fail_open_when_empty=False,
        ),
        selector_ledger_port,
        workflow_aliases=workflow_aliases,
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
    values = _dimension_option_values(
        dimension=dimension,
        options=options,
        exact_run_only=exact_run_only,
        selected_run_id=selected_run_id,
        fallback_value=fallback_value,
    )
    return _filter_options_response(
        response_shape=response_shape,
        dimension=dimension,
        requested_pipeline=requested_pipeline,
        selected_run_types=selected_run_types,
        values=values,
    )
