"""Selector filtering helpers for control-plane HTTP selectors."""

from __future__ import annotations

from bioetl.interfaces.http._control_plane_selector_records import (
    SelectorRecord,
    _without_all_scope_tokens,
)


def filter_records(
    records: tuple[SelectorRecord, ...],
    *,
    selected_workflows: tuple[str, ...],
    selected_pipelines: tuple[str, ...],
    selected_run_types: tuple[str, ...],
    selected_run_statuses: tuple[str, ...],
    selected_run_id: str | None,
) -> tuple[SelectorRecord, ...]:
    if selected_run_id:
        return tuple(record for record in records if record.run_id == selected_run_id)
    workflows = _without_all_scope_tokens(selected_workflows)
    pipelines = _without_all_scope_tokens(selected_pipelines)
    run_types = _without_all_scope_tokens(selected_run_types)
    run_statuses = _without_all_scope_tokens(selected_run_statuses)
    return tuple(
        record
        for record in records
        if _matches_any(workflows, record.workflow_candidates)
        and _matches_one(pipelines, record.pipeline)
        and _matches_one(run_types, record.run_type)
        and _matches_one(run_statuses, record.run_status)
    )


def latest_record(records: tuple[SelectorRecord, ...]) -> SelectorRecord | None:
    if not records:
        return None
    return max(records, key=lambda record: (record.completed_at, record.manifest_id))


def _matches_one(selected: tuple[str, ...], actual: str) -> bool:
    return not selected or actual in selected


def _matches_any(selected: tuple[str, ...], actual_values: tuple[str, ...]) -> bool:
    return not selected or bool(set(selected) & set(actual_values))
