"""Selector record construction helpers for control-plane HTTP selectors."""

from __future__ import annotations

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

ALL_SCOPE = "All"
_ALL_SCOPE_TOKENS = frozenset({ALL_SCOPE, "$__all", "__all", "*"})
_TERMINAL_EVENT_TYPES = frozenset(
    {RUN_FINISHED_EVENT, RUN_FAILED_EVENT, RUN_SHUTDOWN_EVENT}
)


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
    completed_at: datetime
    completed_at_source: str
    run_status: str
    terminal_event_type: str | None


def build_selector_records(
    manifests: tuple[RunManifest, ...],
    ledger_port: RunLedgerLookup | None,
) -> tuple[SelectorRecord, ...]:
    return tuple(
        _build_selector_record(manifest, ledger_port) for manifest in manifests
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
    ledger_port: RunLedgerLookup | None,
) -> SelectorRecord:
    terminal_entry = _latest_terminal_entry(manifest.run_id, ledger_port)
    workflow_candidates = _workflow_candidates(manifest)
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


def _latest_terminal_entry(
    run_id: RunID,
    ledger_port: RunLedgerLookup | None,
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
