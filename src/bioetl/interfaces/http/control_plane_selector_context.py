"""Control-plane selector resolution helpers for Grafana dashboard variables."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.control_plane.run_ledger import (
    RUN_FAILED_EVENT,
    RUN_FINISHED_EVENT,
    RUN_SHUTDOWN_EVENT,
)
from bioetl.domain.types import RunID

RUN_ID_NO_SELECTION = "-"
UNKNOWN_SCOPE = "unknown"
ALL_SCOPE = "All"
SELECTOR_CONTEXT_CONTRACT = "control_plane_selector_context_v1"

_TERMINAL_EVENT_TYPES = frozenset(
    {RUN_FINISHED_EVENT, RUN_FAILED_EVENT, RUN_SHUTDOWN_EVENT}
)


class _RunLedgerLookup(Protocol):
    def list_entries_by_run_id(self, run_id: RunID) -> list[RunLedgerEntry]: ...


@dataclass(frozen=True, slots=True)
class _SelectorRecord:
    manifest: RunManifest
    workflow: str
    workflow_candidates: tuple[str, ...]
    pipeline: str
    run_type: str
    run_id: str
    provider: str
    entity: str
    manifest_id: str
    completed_at: datetime
    completed_at_source: str
    run_status: str
    terminal_event_type: str | None


def build_selector_context_payload(
    *,
    manifests: tuple[RunManifest, ...],
    ledger_port: _RunLedgerLookup | None,
    selected_workflows: tuple[str, ...] = (),
    selected_pipelines: tuple[str, ...] = (),
    selected_run_types: tuple[str, ...] = (),
    selected_run_statuses: tuple[str, ...] = (),
    selected_run_id: str | None = None,
) -> dict[str, object]:
    """Resolve a coherent dashboard selector tuple from local control-plane data."""
    records = _build_selector_records(
        _narrow_manifest_catalog(
            manifests,
            selected_workflows=selected_workflows,
            selected_pipelines=selected_pipelines,
            selected_run_types=selected_run_types,
            selected_run_id=selected_run_id,
        ),
        ledger_port,
    )
    candidates = _filter_records(
        records,
        selected_workflows=selected_workflows,
        selected_pipelines=selected_pipelines,
        selected_run_types=selected_run_types,
        selected_run_statuses=selected_run_statuses,
        selected_run_id=selected_run_id,
    )
    selected = _latest_record(candidates)
    return {
        "contract": SELECTOR_CONTEXT_CONTRACT,
        "resolved_via": _resolved_via(selected, selected_run_id),
        "selected": _selected_payload(selected),
        "options": _options_payload(candidates if candidates else records),
    }


def build_selector_filter_options_payload(
    *,
    manifests: tuple[RunManifest, ...],
    ledger_port: _RunLedgerLookup | None,
    dimension: str,
    response_shape: str,
    requested_pipeline: str | None,
    selected_workflows: tuple[str, ...] = (),
    selected_pipelines: tuple[str, ...] = (),
    selected_run_types: tuple[str, ...] = (),
    selected_run_statuses: tuple[str, ...] = (),
    selected_run_id: str | None = None,
) -> dict[str, object]:
    """Build Grafana variable option responses from the selector catalog."""
    records = _build_selector_records(
        _narrow_manifest_catalog(
            manifests,
            selected_workflows=selected_workflows,
            selected_pipelines=_selected_pipeline_scope(
                selected_pipelines, requested_pipeline
            ),
            selected_run_types=selected_run_types,
            selected_run_id=selected_run_id,
        ),
        ledger_port,
    )
    candidates = _filter_records(
        records,
        selected_workflows=selected_workflows,
        selected_pipelines=selected_pipelines,
        selected_run_types=selected_run_types,
        selected_run_statuses=selected_run_statuses,
        selected_run_id=selected_run_id,
    )
    option_records = candidates if candidates else records
    options = _options_payload(option_records)
    if dimension not in options:
        raise ValueError(f"Unsupported control-plane filter dimension: {dimension}")
    values = list(options[dimension])
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


def _build_selector_records(
    manifests: tuple[RunManifest, ...],
    ledger_port: _RunLedgerLookup | None,
) -> tuple[_SelectorRecord, ...]:
    return tuple(_build_selector_record(manifest, ledger_port) for manifest in manifests)


def _selected_pipeline_scope(
    selected_pipelines: tuple[str, ...],
    requested_pipeline: str | None,
) -> tuple[str, ...]:
    if selected_pipelines:
        return selected_pipelines
    if requested_pipeline in {None, ALL_SCOPE}:
        return ()
    return (requested_pipeline,)


def _narrow_manifest_catalog(
    manifests: tuple[RunManifest, ...],
    *,
    selected_workflows: tuple[str, ...],
    selected_pipelines: tuple[str, ...],
    selected_run_types: tuple[str, ...],
    selected_run_id: str | None,
) -> tuple[RunManifest, ...]:
    """Prune manifest candidates before ledger lookups for selector endpoints.

    The dashboard selector endpoints only need terminal ledger reads for manifests
    that already match cheap manifest-local scope dimensions such as pipeline,
    workflow alias, run type, or exact run ID.
    """
    narrowed = tuple(
        manifest
        for manifest in manifests
        if _manifest_matches_scope(
            manifest,
            selected_workflows=selected_workflows,
            selected_pipelines=selected_pipelines,
            selected_run_types=selected_run_types,
            selected_run_id=selected_run_id,
        )
    )
    return narrowed if narrowed else manifests


def _manifest_matches_scope(
    manifest: RunManifest,
    *,
    selected_workflows: tuple[str, ...],
    selected_pipelines: tuple[str, ...],
    selected_run_types: tuple[str, ...],
    selected_run_id: str | None,
) -> bool:
    if selected_run_id is not None:
        return str(manifest.run_id) == selected_run_id
    if selected_pipelines and manifest.pipeline_name not in selected_pipelines:
        return False
    if selected_run_types and manifest.run_type.value not in selected_run_types:
        return False
    if not selected_workflows:
        return True
    return bool(set(selected_workflows) & set(_workflow_candidates(manifest)))


def _build_selector_record(
    manifest: RunManifest,
    ledger_port: _RunLedgerLookup | None,
) -> _SelectorRecord:
    terminal_entry = _latest_terminal_entry(manifest.run_id, ledger_port)
    workflow_candidates = _workflow_candidates(manifest)
    completed_at = terminal_entry.occurred_at if terminal_entry else manifest.created_at
    return _SelectorRecord(
        manifest=manifest,
        workflow=workflow_candidates[0],
        workflow_candidates=workflow_candidates,
        pipeline=manifest.pipeline_name,
        run_type=manifest.run_type.value,
        run_id=str(manifest.run_id),
        provider=manifest.provider,
        entity=manifest.entity,
        manifest_id=manifest.manifest_id,
        completed_at=completed_at,
        completed_at_source=(
            "run_ledger_terminal_event"
            if terminal_entry
            else "manifest_created_at_fallback"
        ),
        run_status=terminal_entry.status if terminal_entry and terminal_entry.status else "unknown",
        terminal_event_type=terminal_entry.event_type if terminal_entry else None,
    )


def _latest_terminal_entry(
    run_id: RunID,
    ledger_port: _RunLedgerLookup | None,
) -> RunLedgerEntry | None:
    if ledger_port is None:
        return None
    terminal_entries = [
        entry
        for entry in ledger_port.list_entries_by_run_id(run_id)
        if entry.event_type in _TERMINAL_EVENT_TYPES
    ]
    if not terminal_entries:
        return None
    return max(terminal_entries, key=lambda entry: (entry.occurred_at, entry.entry_id))


def _workflow_candidates(manifest: RunManifest) -> tuple[str, ...]:
    candidates: list[str] = []
    for payload in (
        manifest.launch_context,
        manifest.runtime_config,
        manifest.resolved_config,
    ):
        _append_optional_candidate(candidates, payload.get("workflow_name"))
        _append_optional_candidate(candidates, payload.get("workflow"))
    _append_optional_candidate(candidates, manifest.pipeline_name)
    _append_optional_candidate(candidates, f"workflow_{manifest.pipeline_name}")
    return tuple(candidates)


def _append_optional_candidate(candidates: list[str], value: object) -> None:
    if value is None:
        return
    text = str(value).strip()
    if text and text not in candidates:
        candidates.append(text)


def _filter_records(
    records: tuple[_SelectorRecord, ...],
    *,
    selected_workflows: tuple[str, ...],
    selected_pipelines: tuple[str, ...],
    selected_run_types: tuple[str, ...],
    selected_run_statuses: tuple[str, ...],
    selected_run_id: str | None,
) -> tuple[_SelectorRecord, ...]:
    if selected_run_id:
        return tuple(record for record in records if record.run_id == selected_run_id)
    return tuple(
        record
        for record in records
        if _matches_any(selected_workflows, record.workflow_candidates)
        and _matches_one(selected_pipelines, record.pipeline)
        and _matches_one(selected_run_types, record.run_type)
        and _matches_one(selected_run_statuses, record.run_status)
    )


def _matches_one(selected: tuple[str, ...], actual: str) -> bool:
    return not selected or actual in selected


def _matches_any(selected: tuple[str, ...], actual_values: tuple[str, ...]) -> bool:
    return not selected or bool(set(selected) & set(actual_values))


def _latest_record(records: tuple[_SelectorRecord, ...]) -> _SelectorRecord | None:
    if not records:
        return None
    return max(records, key=lambda record: (record.completed_at, record.manifest_id))


def _resolved_via(
    selected: _SelectorRecord | None,
    selected_run_id: str | None,
) -> str:
    if selected is None:
        return "no_manifest_for_scope"
    if selected_run_id:
        return "selected_run_id"
    if selected.completed_at_source == "run_ledger_terminal_event":
        return "latest_terminal_run_for_scope"
    return "latest_manifest_created_at_for_scope"


def _selected_payload(record: _SelectorRecord | None) -> dict[str, object]:
    if record is None:
        return {
            "workflow": ALL_SCOPE,
            "pipeline": UNKNOWN_SCOPE,
            "run_type": ALL_SCOPE,
            "run_id": RUN_ID_NO_SELECTION,
            "run_status": UNKNOWN_SCOPE,
            "provider": UNKNOWN_SCOPE,
            "entity": UNKNOWN_SCOPE,
            "manifest_id": "",
            "completed_at": "",
            "completed_at_source": "none",
            "terminal_event_type": "",
        }
    return {
        "workflow": record.workflow,
        "pipeline": record.pipeline,
        "run_type": record.run_type,
        "run_id": record.run_id,
        "run_status": record.run_status,
        "provider": record.provider,
        "entity": record.entity,
        "manifest_id": record.manifest_id,
        "completed_at": record.completed_at.isoformat(),
        "completed_at_source": record.completed_at_source,
        "terminal_event_type": record.terminal_event_type or "",
    }


def _options_payload(records: tuple[_SelectorRecord, ...]) -> dict[str, list[str]]:
    return {
        "workflow": _latest_ordered_values(records, lambda record: (record.workflow,)),
        "pipeline": _latest_ordered_values(records, lambda record: (record.pipeline,)),
        "run_type": _latest_ordered_values(records, lambda record: (record.run_type,)),
        "run_id": _manifest_ordered_values(records, lambda record: record.run_id),
        "run_status": _latest_ordered_values(
            records,
            lambda record: (record.run_status,),
            skip_unknown=False,
        ),
    }


def _latest_ordered_values(
    records: tuple[_SelectorRecord, ...],
    value_factory: Callable[[_SelectorRecord], tuple[str, ...]],
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


def _manifest_ordered_values(
    records: tuple[_SelectorRecord, ...],
    value_factory: Callable[[_SelectorRecord], str],
) -> list[str]:
    values: list[str] = []
    for record in records:
        value = value_factory(record)
        if value and value not in values:
            values.append(value)
    return values
