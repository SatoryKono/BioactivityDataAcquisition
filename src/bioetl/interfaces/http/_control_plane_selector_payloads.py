"""Selector payload rendering helpers for control-plane HTTP selectors."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from bioetl.interfaces.http._control_plane_selector_records import (
    ALL_SCOPE,
    SelectorRecord,
)

RUN_ID_NO_SELECTION = "-"
RUN_ID_NO_RUNS_LABEL = "НЕТ ЗАПУСКОВ"
UNKNOWN_SCOPE = "unknown"
RUN_TYPE_FALLBACK = "backfill"
SELECTOR_CONTEXT_CONTRACT = "control_plane_selector_context_v1"
DEFAULTS_POLICY = "last_run_truthful"
RUN_ID_LIST_ORDER = "started_at_desc"
RESOLVED_VIA_A2 = "latest_a2_for_scope"


def resolved_via(
    selected: SelectorRecord | None,
    selected_run_id: str | None,
    *,
    auto_selected: bool = False,
    selected_present: bool = False,
) -> str:
    if selected is None and not selected_present:
        return "no_manifest_for_scope"
    if auto_selected:
        # Distinct from explicit URL/UI run_id so Grafana last-run defaults
        # (applyRunId=false) still write var-run_id from selected.run_id.
        return RESOLVED_VIA_A2
    if selected_run_id:
        return "selected_run_id"
    if selected is not None and selected.completed_at_source == "run_ledger_terminal_event":
        return "latest_terminal_run_for_scope"
    return "latest_manifest_created_at_for_scope"


def defaults_payload() -> dict[str, object]:
    """Machine-readable default policy for selector-shell clients (SEL-P0/P1)."""
    return {
        "policy": DEFAULTS_POLICY,
        "run_type_fallback": RUN_TYPE_FALLBACK,
        "overview_landing": "fleet_all",
        "run_id_list_order": RUN_ID_LIST_ORDER,
        "url_var_precedence": "url_wins",
        "non_overview_native_run_type_default": RUN_TYPE_FALLBACK,
    }


def selected_payload(record: SelectorRecord | None) -> dict[str, object]:
    if record is None:
        return _empty_selected_payload()
    return {
        "workflow": record.workflow,
        "pipeline": record.pipeline,
        "run_type": record.run_type,
        "run_id": record.run_id,
        "run_status": record.run_status,
        "provider": record.provider,
        "entity": record.entity,
        "manifest_id": record.manifest_id,
        "started_at": record.started_at.isoformat(),
        "started_at_source": record.started_at_source,
        "completed_at": record.completed_at.isoformat(),
        "completed_at_source": record.completed_at_source,
        "terminal_event_type": record.terminal_event_type or "",
    }


def selected_payload_from_report_identity(
    identity: dict[str, object],
) -> dict[str, object]:
    """Build ``selected`` from a verified pipeline-run-report identity."""
    pipeline = str(identity.get("pipeline_name") or UNKNOWN_SCOPE)
    provider, separator, entity = pipeline.partition("_")
    if not separator:
        provider, entity = UNKNOWN_SCOPE, UNKNOWN_SCOPE
    workflow = identity.get("workflow_id")
    run_type = identity.get("run_type")
    run_id = identity.get("run_id")
    status = identity.get("status")
    started = identity.get("started_at")
    completed = identity.get("completed_at")
    return {
        "workflow": str(workflow) if isinstance(workflow, str) and workflow else ALL_SCOPE,
        "pipeline": pipeline,
        "run_type": (
            str(run_type) if isinstance(run_type, str) and run_type else RUN_TYPE_FALLBACK
        ),
        "run_id": str(run_id) if isinstance(run_id, str) and run_id else RUN_ID_NO_SELECTION,
        "run_status": (
            str(status) if isinstance(status, str) and status else UNKNOWN_SCOPE
        ),
        "provider": provider or UNKNOWN_SCOPE,
        "entity": entity or UNKNOWN_SCOPE,
        "manifest_id": "",
        "started_at": str(started) if isinstance(started, str) else "",
        "started_at_source": "pipeline_run_report",
        "completed_at": str(completed) if isinstance(completed, str) else "",
        "completed_at_source": (
            "pipeline_run_report" if isinstance(completed, str) and completed else "none"
        ),
        "terminal_event_type": "",
    }


def _empty_selected_payload() -> dict[str, object]:
    return {
        "workflow": ALL_SCOPE,
        "pipeline": UNKNOWN_SCOPE,
        "run_type": RUN_TYPE_FALLBACK,
        "run_id": RUN_ID_NO_SELECTION,
        "run_status": UNKNOWN_SCOPE,
        "provider": UNKNOWN_SCOPE,
        "entity": UNKNOWN_SCOPE,
        "manifest_id": "",
        "started_at": "",
        "started_at_source": "none",
        "completed_at": "",
        "completed_at_source": "none",
        "terminal_event_type": "",
    }


def options_payload(records: tuple[SelectorRecord, ...]) -> dict[str, list[str]]:
    return {
        "workflow": _latest_ordered_values(records, lambda record: (record.workflow,)),
        "pipeline": _latest_ordered_values(records, lambda record: (record.pipeline,)),
        "run_type": _latest_ordered_values(records, lambda record: (record.run_type,)),
        "provider": _latest_ordered_values(records, lambda record: (record.provider,)),
        "run_id": _started_at_ordered_values(records, lambda record: record.run_id),
        "run_status": _latest_ordered_values(
            records,
            lambda record: (record.run_status,),
            skip_unknown=False,
        ),
    }


def exact_run_only_fallback_values(fallback_value: str | None) -> list[str]:
    if fallback_value is None:
        return []
    value = fallback_value.strip()
    if not value:
        return []
    return [value]


def _latest_ordered_values(
    records: tuple[SelectorRecord, ...],
    value_factory: Callable[[SelectorRecord], tuple[str, ...]],
    *,
    skip_unknown: bool = True,
) -> list[str]:
    latest_by_value: dict[str, tuple[datetime, str]] = {}
    for record in records:
        values = value_factory(record)
        for value in values:
            if skip_unknown and value == UNKNOWN_SCOPE:
                continue
            current = latest_by_value.get(value)
            candidate = (record.completed_at, record.manifest_id)
            if current is None or candidate > current:
                latest_by_value[value] = candidate
    return [
        value
        for value, _sort_key in sorted(
            latest_by_value.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]


def _started_at_ordered_values(
    records: tuple[SelectorRecord, ...],
    value_factory: Callable[[SelectorRecord], str],
) -> list[str]:
    """Order unique run_id values by started_at desc (newest first).

    Tie-break: manifest_id, then run_id for deterministic ordering.
    """
    best_by_value: dict[str, tuple[datetime, str, str]] = {}
    for record in records:
        value = value_factory(record)
        if not value:
            continue
        candidate = (record.started_at, record.manifest_id, record.run_id)
        current = best_by_value.get(value)
        if current is None or candidate > current:
            best_by_value[value] = candidate
    return [
        value
        for value, _sort_key in sorted(
            best_by_value.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]


# Backward-compatible alias used by existing unit tests and importers.
_manifest_ordered_values = _started_at_ordered_values
