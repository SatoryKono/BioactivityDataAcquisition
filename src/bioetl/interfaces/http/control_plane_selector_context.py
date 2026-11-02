"""Control-plane selector resolution helpers for Grafana dashboard variables."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC

from bioetl.domain.control_plane import RunManifest, WorkflowManifest
from bioetl.interfaces.http._control_plane_selector_filters import (
    filter_records,
    latest_record,
)
from bioetl.interfaces.http._control_plane_selector_payloads import (
    RUN_ID_NO_RUNS_LABEL,
    RUN_ID_NO_SELECTION,
    SELECTOR_CONTEXT_CONTRACT,
    UNKNOWN_SCOPE,
    defaults_payload,
    exact_run_only_fallback_values,
    options_payload,
    resolved_via,
    selected_payload,
    selected_payload_from_report_identity,
)
from bioetl.interfaces.http._control_plane_selector_records import (
    RunLedgerLookup,
    SelectorRecord,
    build_selector_records,
    build_workflow_aliases,
    narrow_manifest_catalog,
    selected_pipeline_scope,
)
from bioetl.interfaces.http._identity_display_rows import format_timestamp_label

__all__ = (
    "RUN_ID_NO_SELECTION",
    "SELECTOR_CONTEXT_CONTRACT",
    "UNKNOWN_SCOPE",
    "RunIdOptionPolicy",
    "build_selector_context_payload",
    "build_selector_filter_options_payload",
)


@dataclass(frozen=True, slots=True)
class RunIdOptionPolicy:
    """Exact-run option policy for Grafana variable queries."""

    exact_run_only: bool = False
    fallback_value: str | None = None


_DEFAULT_RUN_ID_OPTION_POLICY = RunIdOptionPolicy()


@dataclass(frozen=True, slots=True)
class _SelectionOutcome:
    selected_out: dict[str, object]
    via: str
    option_records: tuple[SelectorRecord, ...]


def build_selector_context_payload(
    *,
    manifests: tuple[RunManifest, ...],
    ledger_port: RunLedgerLookup | None,
    selected_workflows: tuple[str, ...] = (),
    selected_pipelines: tuple[str, ...] = (),
    selected_run_types: tuple[str, ...] = (),
    selected_run_statuses: tuple[str, ...] = (),
    selected_run_id: str | None = None,
    auto_selected_run_id: str | None = None,
    report_selected: Mapping[str, object] | None = None,
    workflow_manifests: tuple[WorkflowManifest, ...] = (),
    a2_consulted: bool = False,
) -> dict[str, object]:
    """Resolve a coherent dashboard selector tuple from local control-plane data.

    ``selected_run_id`` is an explicit client/URL choice (``resolved_via=
    selected_run_id``). ``auto_selected_run_id`` is A2 fill from an unresolved
    selector and keeps the last-run defaults signal (``latest_a2_for_scope``).
    ``report_selected`` supplies a verified report identity when the picked
    UUID exists only in saved pipeline-run reports (auto or explicit).
    ``a2_consulted`` means A2 already decided the unresolved scope: when it
    returned ``None``, keep empty selected and do **not** re-pick via
    pipeline-wide workflow aliases (foreign-workflow data must not leak into
    ``${selected_run_id}`` panels). When a run is selected, ``selected.pipeline``
    is always the concrete pipeline name so report/artifact clients can follow
    it even if the Grafana ``pipeline`` var is still aggregate (All / ``.*``).
    """
    workflow_aliases = build_workflow_aliases(workflow_manifests)
    explicit_run_id = selected_run_id
    auto_run_id = None if explicit_run_id else auto_selected_run_id
    records = build_selector_records(
        narrow_manifest_catalog(
            manifests,
            selected_workflows=selected_workflows,
            selected_pipelines=selected_pipelines,
            selected_run_types=selected_run_types,
            selected_run_id=explicit_run_id,
            workflow_aliases=workflow_aliases,
        ),
        ledger_port,
        workflow_aliases=workflow_aliases,
    )
    scope_candidates = filter_records(
        records,
        selected_workflows=selected_workflows,
        selected_pipelines=selected_pipelines,
        selected_run_types=selected_run_types,
        selected_run_statuses=selected_run_statuses,
        selected_run_id=None,
    )
    outcome = _resolve_selection_outcome(
        records=records,
        scope_candidates=scope_candidates,
        selected_workflows=selected_workflows,
        selected_pipelines=selected_pipelines,
        selected_run_types=selected_run_types,
        selected_run_statuses=selected_run_statuses,
        explicit_run_id=explicit_run_id,
        auto_run_id=auto_run_id,
        report_selected=report_selected,
        a2_consulted=a2_consulted,
    )
    return {
        "contract": SELECTOR_CONTEXT_CONTRACT,
        "resolved_via": outcome.via,
        "selected": outcome.selected_out,
        "options": options_payload(outcome.option_records),
        "defaults": defaults_payload(),
    }


def _resolve_selection_outcome(
    *,
    records: tuple[SelectorRecord, ...],
    scope_candidates: tuple[SelectorRecord, ...],
    selected_workflows: tuple[str, ...],
    selected_pipelines: tuple[str, ...],
    selected_run_types: tuple[str, ...],
    selected_run_statuses: tuple[str, ...],
    explicit_run_id: str | None,
    auto_run_id: str | None,
    report_selected: Mapping[str, object] | None,
    a2_consulted: bool,
) -> _SelectionOutcome:
    if explicit_run_id:
        return _explicit_run_selection(
            records=records,
            selected_workflows=selected_workflows,
            selected_pipelines=selected_pipelines,
            selected_run_types=selected_run_types,
            selected_run_statuses=selected_run_statuses,
            explicit_run_id=explicit_run_id,
            report_selected=report_selected,
        )
    if auto_run_id:
        return _auto_run_selection(
            records=records,
            scope_candidates=scope_candidates,
            auto_run_id=auto_run_id,
            report_selected=report_selected,
        )
    if a2_consulted:
        # Strict A2 empty scope: do not fall back to alias-broad latest_record.
        return _SelectionOutcome(
            selected_out=selected_payload(None),
            via=resolved_via(None, None, auto_selected=False),
            option_records=scope_candidates if scope_candidates else records,
        )
    selected = latest_record(scope_candidates)
    return _SelectionOutcome(
        selected_out=selected_payload(selected),
        via=resolved_via(selected, None, auto_selected=False),
        option_records=scope_candidates if scope_candidates else records,
    )


def _selection_from_manifest_or_report(
    *,
    selected: SelectorRecord | None,
    report_selected: Mapping[str, object] | None,
    explicit_run_id: str | None,
    auto_selected: bool,
) -> tuple[dict[str, object], str]:
    if selected is not None:
        return (
            selected_payload(selected),
            resolved_via(selected, explicit_run_id, auto_selected=auto_selected),
        )
    if report_selected is not None:
        return (
            selected_payload_from_report_identity(dict(report_selected)),
            resolved_via(
                None,
                explicit_run_id,
                auto_selected=auto_selected,
                selected_present=True,
            ),
        )
    return (
        selected_payload(None),
        resolved_via(None, explicit_run_id, auto_selected=False),
    )


def _explicit_run_selection(
    *,
    records: tuple[SelectorRecord, ...],
    selected_workflows: tuple[str, ...],
    selected_pipelines: tuple[str, ...],
    selected_run_types: tuple[str, ...],
    selected_run_statuses: tuple[str, ...],
    explicit_run_id: str,
    report_selected: Mapping[str, object] | None,
) -> _SelectionOutcome:
    candidates = filter_records(
        records,
        selected_workflows=selected_workflows,
        selected_pipelines=selected_pipelines,
        selected_run_types=selected_run_types,
        selected_run_statuses=selected_run_statuses,
        selected_run_id=explicit_run_id,
    )
    selected_out, via = _selection_from_manifest_or_report(
        selected=latest_record(candidates),
        report_selected=report_selected,
        explicit_run_id=explicit_run_id,
        auto_selected=False,
    )
    return _SelectionOutcome(
        selected_out=selected_out,
        via=via,
        option_records=candidates if candidates else records,
    )


def _auto_run_selection(
    *,
    records: tuple[SelectorRecord, ...],
    scope_candidates: tuple[SelectorRecord, ...],
    auto_run_id: str,
    report_selected: Mapping[str, object] | None,
) -> _SelectionOutcome:
    selected = _record_for_a2_run_id(
        auto_run_id, scope_candidates=scope_candidates, records=records
    )
    selected_out, via = _selection_from_manifest_or_report(
        selected=selected,
        report_selected=report_selected,
        explicit_run_id=None,
        auto_selected=True,
    )
    return _SelectionOutcome(
        selected_out=selected_out,
        via=via,
        option_records=scope_candidates if scope_candidates else records,
    )


def _record_for_a2_run_id(
    auto_run_id: str,
    *,
    scope_candidates: tuple[SelectorRecord, ...],
    records: tuple[SelectorRecord, ...],
) -> SelectorRecord | None:
    """Prefer scoped match; fall back to full catalog for A2-validated UUIDs.

    A2 already enforced declared workflow membership (incl. top-level
    ``RunManifest.workflow_name``). Legacy scope filters must not drop that
    pick when candidates briefly lag unified membership.
    """
    scoped = next(
        (record for record in scope_candidates if record.run_id == auto_run_id),
        None,
    )
    if scoped is not None:
        return scoped
    return next(
        (record for record in records if record.run_id == auto_run_id),
        None,
    )


def _selector_ledger_for_dimension(
    dimension: str,
    selected_run_statuses: tuple[str, ...],
    ledger_port: RunLedgerLookup | None,
) -> RunLedgerLookup | None:
    if dimension != "run_status" and not selected_run_statuses:
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
    if dimension == "run_id":
        return [RUN_ID_NO_SELECTION, *[value for value in values if value]]
    if dimension == "pipeline":
        return [
            UNKNOWN_SCOPE,
            *[value for value in values if value and value != UNKNOWN_SCOPE],
        ]
    return values


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
    if response_shape == "options":
        # The legacy list sentinel is not an observed pipeline. Let Grafana's
        # empty-options mapping show NO MATCHES for a successful empty scope.
        if dimension == "pipeline" and values == [UNKNOWN_SCOPE]:
            return {"items": []}
        return {"items": [{"text": value, "value": value} for value in values]}
    if response_shape == "list":
        return {"items": values}
    return {
        "contract": SELECTOR_CONTEXT_CONTRACT,
        "dimension": dimension,
        "pipeline": requested_pipeline,
        "run_type": list(selected_run_types),
        "items": values,
    }


def _run_option_label(
    value: str,
    record: SelectorRecord | None,
    *,
    timezone: str = "UTC",
    empty_catalog: bool = False,
) -> str:
    """Readable catalog label; Grafana value stays the stable UUID."""
    if value == RUN_ID_NO_SELECTION:
        # A2 empty catalog uses «НЕТ ЗАПУСКОВ»; SELECT RUN remains only as the
        # legacy A1 sentinel label when concrete runs exist (JSON may still send -).
        return RUN_ID_NO_RUNS_LABEL if empty_catalog else "SELECT RUN"
    if record is None:
        return f"UNKNOWN · {value}"
    timestamp = record.started_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    started = format_timestamp_label(timestamp, timezone)
    return f"{started} · {record.pipeline} · {record.run_status} · {record.run_id}"


def _run_option_labels(
    values: list[str],
    records: tuple[SelectorRecord, ...],
    *,
    timezone: str = "UTC",
) -> dict[str, object]:
    by_id = {record.run_id: record for record in records}
    concrete = [value for value in values if value and value != RUN_ID_NO_SELECTION]
    empty_catalog = not concrete
    if empty_catalog:
        return {
            "items": [
                {"text": RUN_ID_NO_RUNS_LABEL, "value": RUN_ID_NO_SELECTION},
            ]
        }
    items = [
        {
            "text": _run_option_label(
                value,
                by_id.get(value),
                timezone=timezone,
                empty_catalog=False,
            ),
            "value": value,
        }
        for value in values
    ]
    return {"items": items}


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
    run_id_policy: RunIdOptionPolicy = _DEFAULT_RUN_ID_OPTION_POLICY,
    workflow_manifests: tuple[WorkflowManifest, ...] = (),
    timezone: str = "UTC",
) -> dict[str, object]:
    """Build Grafana variable option responses from the selector catalog."""
    workflow_aliases = build_workflow_aliases(workflow_manifests)
    selector_ledger_port = _selector_ledger_for_dimension(
        dimension,
        selected_run_statuses,
        ledger_port,
    )
    if response_shape == "options" and dimension == "run_id":
        selector_ledger_port = ledger_port
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
        exact_run_only=run_id_policy.exact_run_only,
        selected_run_id=selected_run_id,
        fallback_value=run_id_policy.fallback_value,
    )
    if response_shape == "options" and dimension == "run_id":
        return _run_option_labels(values, option_records, timezone=timezone)
    return _filter_options_response(
        response_shape=response_shape,
        dimension=dimension,
        requested_pipeline=requested_pipeline,
        selected_run_types=selected_run_types,
        values=values,
    )
