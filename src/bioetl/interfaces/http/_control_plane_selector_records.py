"""Selector record construction helpers for control-plane HTTP selectors."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from bioetl.domain.control_plane import RunLedgerEntry, RunManifest, WorkflowManifest
from bioetl.domain.control_plane.run_ledger import (
    RUN_FAILED_EVENT,
    RUN_FINISHED_EVENT,
    RUN_SHUTDOWN_EVENT,
    RUN_STARTED_EVENT,
)
from bioetl.domain.types import RunID

ALL_SCOPE = "All"
_ALL_SCOPE_TOKENS = frozenset({ALL_SCOPE, "$__all", "__all", "*"})
_TERMINAL_EVENT_TYPES = frozenset(
    {RUN_FINISHED_EVENT, RUN_FAILED_EVENT, RUN_SHUTDOWN_EVENT}
)
WorkflowAliasMap = dict[tuple[str, str | None], tuple[str, ...]]


class RunLedgerLookup(Protocol):
    def list_entries_by_run_id(self, run_id: RunID) -> list[RunLedgerEntry]: ...


@dataclass(frozen=True, slots=True)
class SelectorRecord:
    manifest: RunManifest
    workflow: str
    workflow_candidates: tuple[str, ...]
    pipeline: str
    run_type: str
    run_id: str
    provider: str
    entity: str
    manifest_id: str
    started_at: datetime
    started_at_source: str
    completed_at: datetime
    completed_at_source: str
    run_status: str
    terminal_event_type: str | None


def build_selector_records(
    manifests: tuple[RunManifest, ...],
    ledger_port: RunLedgerLookup | None,
    workflow_aliases: WorkflowAliasMap | None = None,
) -> tuple[SelectorRecord, ...]:
    return tuple(
        _build_selector_record(manifest, ledger_port, workflow_aliases)
        for manifest in manifests
    )


def selected_pipeline_scope(
    selected_pipelines: tuple[str, ...],
    requested_pipeline: str | None,
) -> tuple[str, ...]:
    if selected_pipelines:
        return selected_pipelines
    if requested_pipeline is None or requested_pipeline.strip() in _ALL_SCOPE_TOKENS:
        return ()
    return (requested_pipeline,)


def narrow_manifest_catalog(
    manifests: tuple[RunManifest, ...],
    *,
    selected_workflows: tuple[str, ...],
    selected_pipelines: tuple[str, ...],
    selected_run_types: tuple[str, ...],
    selected_run_id: str | None,
    workflow_aliases: WorkflowAliasMap | None = None,
    fail_open_when_empty: bool = True,
) -> tuple[RunManifest, ...]:
    """Prune manifest candidates before ledger lookups for selector endpoints."""
    narrowed = tuple(
        manifest
        for manifest in manifests
        if _manifest_matches_scope(
            manifest,
            selected_workflows=selected_workflows,
            selected_pipelines=selected_pipelines,
            selected_run_types=selected_run_types,
            selected_run_id=selected_run_id,
            workflow_aliases=workflow_aliases,
        )
    )
    if narrowed or not fail_open_when_empty:
        return narrowed
    return manifests


def _manifest_matches_scope(
    manifest: RunManifest,
    *,
    selected_workflows: tuple[str, ...],
    selected_pipelines: tuple[str, ...],
    selected_run_types: tuple[str, ...],
    selected_run_id: str | None,
    workflow_aliases: WorkflowAliasMap | None,
) -> bool:
    if selected_run_id is not None:
        return str(manifest.run_id) == selected_run_id
    if selected_pipelines and manifest.pipeline_name not in selected_pipelines:
        return False
    if selected_run_types and manifest.run_type.value not in selected_run_types:
        return False
    if not selected_workflows:
        return True
    return bool(
        set(selected_workflows) & set(_workflow_candidates(manifest, workflow_aliases))
    )


def build_workflow_aliases(
    workflow_manifests: tuple[WorkflowManifest, ...],
) -> WorkflowAliasMap:
    """Map pipeline/run_type tuples to workflow names from workflow manifests."""
    aliases: dict[tuple[str, str | None], list[str]] = {}
    for workflow_manifest in workflow_manifests:
        selected_step_ids = set(workflow_manifest.selected_step_ids)
        for step in workflow_manifest.steps:
            if selected_step_ids and step.step_id not in selected_step_ids:
                continue
            pipeline_name = _optional_text(step.pipeline_name)
            if pipeline_name is None:
                continue
            run_type = _workflow_step_run_type(
                step.run_options,
                workflow_manifest.defaults,
            )
            bucket = aliases.setdefault((pipeline_name, run_type), [])
            if workflow_manifest.workflow_name not in bucket:
                bucket.append(workflow_manifest.workflow_name)
    return {key: tuple(values) for key, values in aliases.items()}


def _build_selector_record(
    manifest: RunManifest,
    ledger_port: RunLedgerLookup | None,
    workflow_aliases: WorkflowAliasMap | None,
) -> SelectorRecord:
    ledger_entries = (
        tuple(ledger_port.list_entries_by_run_id(manifest.run_id))
        if ledger_port is not None
        else ()
    )
    started_entry = _latest_started_entry(ledger_entries)
    terminal_entry = _latest_terminal_entry(ledger_entries)
    workflow_candidates = _workflow_candidates(manifest, workflow_aliases)
    started_at = started_entry.occurred_at if started_entry else manifest.created_at
    completed_at = terminal_entry.occurred_at if terminal_entry else manifest.created_at
    return SelectorRecord(
        manifest=manifest,
        workflow=workflow_candidates[0],
        workflow_candidates=workflow_candidates,
        pipeline=manifest.pipeline_name,
        run_type=manifest.run_type.value,
        run_id=str(manifest.run_id),
        provider=manifest.provider,
        entity=manifest.entity,
        manifest_id=manifest.manifest_id,
        started_at=started_at,
        started_at_source=(
            "run_ledger_started_event"
            if started_entry
            else "manifest_created_at_fallback"
        ),
        completed_at=completed_at,
        completed_at_source=(
            "run_ledger_terminal_event"
            if terminal_entry
            else "manifest_created_at_fallback"
        ),
        run_status=terminal_entry.status
        if terminal_entry and terminal_entry.status
        else "unknown",
        terminal_event_type=terminal_entry.event_type if terminal_entry else None,
    )


def _latest_started_entry(
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> RunLedgerEntry | None:
    started_entries = [
        entry for entry in ledger_entries if entry.event_type == RUN_STARTED_EVENT
    ]
    if not started_entries:
        return None
    return min(started_entries, key=lambda entry: (entry.occurred_at, entry.entry_id))


def _latest_terminal_entry(
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> RunLedgerEntry | None:
    terminal_entries = [
        entry for entry in ledger_entries if entry.event_type in _TERMINAL_EVENT_TYPES
    ]
    if not terminal_entries:
        return None
    return max(terminal_entries, key=lambda entry: (entry.occurred_at, entry.entry_id))


def _workflow_candidates(
    manifest: RunManifest,
    workflow_aliases: WorkflowAliasMap | None = None,
) -> tuple[str, ...]:
    candidates: list[str] = []
    for payload in (
        manifest.launch_context,
        manifest.runtime_config,
        manifest.resolved_config,
    ):
        _append_optional_candidate(candidates, payload.get("workflow_name"))
        _append_optional_candidate(candidates, payload.get("workflow"))
    for alias in _workflow_alias_candidates(manifest, workflow_aliases):
        _append_optional_candidate(candidates, alias)
    _append_optional_candidate(candidates, manifest.pipeline_name)
    _append_optional_candidate(candidates, f"workflow_{manifest.pipeline_name}")
    return tuple(candidates)


def _workflow_alias_candidates(
    manifest: RunManifest,
    workflow_aliases: WorkflowAliasMap | None,
) -> tuple[str, ...]:
    if not workflow_aliases:
        return ()
    return (
        *workflow_aliases.get((manifest.pipeline_name, manifest.run_type.value), ()),
        *workflow_aliases.get((manifest.pipeline_name, None), ()),
    )


def _workflow_step_run_type(
    run_options: dict[str, object] | None,
    defaults: dict[str, object],
) -> str | None:
    return _optional_text((run_options or {}).get("run_type")) or _optional_text(
        defaults.get("run_type")
    )


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _append_optional_candidate(candidates: list[str], value: object) -> None:
    if value is None:
        return
    text = str(value).strip()
    if text and text not in candidates:
        candidates.append(text)
