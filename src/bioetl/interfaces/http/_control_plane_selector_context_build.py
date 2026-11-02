"""Build selected-run selector context payloads from local catalogs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from bioetl.domain.control_plane import RunManifest, WorkflowManifest
from bioetl.interfaces.http._control_plane_selector_filters import (
    filter_records,
    latest_record,
)
from bioetl.interfaces.http._control_plane_selector_payloads import (
    SELECTOR_CONTEXT_CONTRACT,
    defaults_payload,
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
)


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

    ``selected_run_id`` is an explicit client/URL choice. ``auto_selected_run_id``
    is A2 fill from an unresolved selector. ``report_selected`` supplies a
    verified report identity when the picked UUID exists only in saved reports.
    When A2 consulted a strict scope and returned ``None``, keep the selection
    empty instead of re-picking from pipeline-wide aliases.
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
    """Prefer scoped match; fall back to full catalog for A2-validated UUIDs."""
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
