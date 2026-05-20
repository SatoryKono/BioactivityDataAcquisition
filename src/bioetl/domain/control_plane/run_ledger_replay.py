"""Pure run-ledger replay projection helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import TypedDict, cast

from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.control_plane._run_ledger_runtime import (
    ARTIFACT_PUBLISHED_EVENT,
    COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
    COMPOSITE_ENRICHER_COMPLETED_EVENT,
    COMPOSITE_MERGE_COMPLETED_EVENT,
    DQ_POLICY_APPLIED_EVENT,
    INPUT_SNAPSHOT_PUBLISHED_EVENT,
    MANIFEST_CREATED_EVENT,
    RUN_FAILED_EVENT,
    RUN_FINISHED_EVENT,
    RUN_SHUTDOWN_EVENT,
    RUN_STARTED_EVENT,
    STAGE_STARTED_EVENT,
    STAGE_COMPLETED_EVENT,
    RunLedgerEntry,
)

__all__ = ["RunLedgerReplayProjection", "project_run_ledger_replay"]


@dataclass(frozen=True, slots=True)
class RunLedgerReplayProjection:
    """Deterministic replay delta for durable composite resume milestones."""

    state: CompositePipelineState | None = None
    seed_completed: bool | None = None
    merge_completed: bool | None = None
    completed_dependencies: frozenset[str] = frozenset()
    dependency_results: dict[str, DependencyResult] = field(default_factory=dict)
    completed_enrichers: frozenset[str] = frozenset()
    enrichment_results: dict[str, EnrichmentResult] = field(default_factory=dict)
    merge_result: dict[str, object] | None = None
    input_snapshots: tuple[dict[str, object], ...] = ()
    last_event_id: str | None = None
    last_event_occurred_at: datetime | None = None
    replayed_entry_count: int = 0
    projection_contract: str = "checkpoint_snapshot_plus_ledger_suffix_resume"
    projector_coverage_complete: bool = True
    unsupported_replay_entries: tuple[tuple[str, str, str | None], ...] = ()


class _StageCompletionUpdate(TypedDict, total=False):
    state: CompositePipelineState
    seed_completed: bool
    merge_completed: bool


_ProjectionFn = Callable[
    [RunLedgerReplayProjection, RunLedgerEntry],
    RunLedgerReplayProjection,
]


_STAGE_COMPLETION_UPDATES: dict[str, _StageCompletionUpdate] = {
    "seed": {
        "state": CompositePipelineState.SEED_COMPLETED,
        "seed_completed": True,
    },
    "dependencies": {
        "state": CompositePipelineState.DEPENDENCIES_COMPLETED,
    },
    "enrichment": {
        "state": CompositePipelineState.ENRICHMENT_COMPLETED,
    },
    "merge": {
        "state": CompositePipelineState.MERGING,
        "merge_completed": True,
    },
}


def _project_stage_completed(
    projection: RunLedgerReplayProjection,
    entry: RunLedgerEntry,
) -> RunLedgerReplayProjection:
    update = _STAGE_COMPLETION_UPDATES.get((entry.stage or "").strip().lower())
    if update is None:
        return projection
    return cast(
        RunLedgerReplayProjection,
        replace(projection, **update),
    )


def _details(entry: RunLedgerEntry) -> dict[str, object]:
    """Return ledger details without diagnostic metadata."""
    if not isinstance(entry.details, dict):
        return {}
    return {
        str(key): value
        for key, value in entry.details.items()
        if str(key) != "_diagnostic"
    }


def _optional_text(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_value(payload: dict[str, object], key: str) -> int:
    try:
        return int(payload.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _float_value(payload: dict[str, object], key: str) -> float:
    try:
        return float(payload.get(key, 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _project_composite_dependency_completed(
    projection: RunLedgerReplayProjection,
    entry: RunLedgerEntry,
) -> RunLedgerReplayProjection:
    payload = _details(entry)
    dependency_name = _optional_text(payload, "dependency_name")
    pipeline_name = _optional_text(payload, "pipeline_name") or dependency_name
    if dependency_name is None or pipeline_name is None:
        return projection
    dependency_results = dict(projection.dependency_results)
    dependency_results[dependency_name] = DependencyResult(
        pipeline_name=pipeline_name,
        status=DependencyStatus(str(payload.get("status", "success"))),
        records_extracted=_int_value(payload, "records_extracted"),
        records_silver=_int_value(payload, "records_silver"),
        duration_seconds=_float_value(payload, "duration_seconds"),
        error_message=_optional_text(payload, "error_message"),
        resumed=bool(payload.get("resumed", False)),
    )
    return replace(
        projection,
        completed_dependencies=frozenset(
            {*projection.completed_dependencies, dependency_name}
        ),
        dependency_results=dict(sorted(dependency_results.items())),
    )


def _project_composite_enricher_completed(
    projection: RunLedgerReplayProjection,
    entry: RunLedgerEntry,
) -> RunLedgerReplayProjection:
    payload = _details(entry)
    enricher_name = _optional_text(payload, "enricher_name")
    if enricher_name is None:
        return projection
    enrichment_results = dict(projection.enrichment_results)
    enrichment_results[enricher_name] = EnrichmentResult(
        enricher_name=enricher_name,
        status=EnrichmentStatus(str(payload.get("status", "success"))),
        records_input=_int_value(payload, "records_input"),
        records_enriched=_int_value(payload, "records_enriched"),
        records_not_found=_int_value(payload, "records_not_found"),
        records_errored=_int_value(payload, "records_errored"),
        dq_error_rate=_float_value(payload, "dq_error_rate"),
        duration_seconds=_float_value(payload, "duration_seconds"),
        error_message=_optional_text(payload, "error_message"),
    )
    return replace(
        projection,
        completed_enrichers=frozenset({*projection.completed_enrichers, enricher_name}),
        enrichment_results=dict(sorted(enrichment_results.items())),
    )


def _project_composite_merge_completed(
    projection: RunLedgerReplayProjection,
    entry: RunLedgerEntry,
) -> RunLedgerReplayProjection:
    payload = _details(entry)
    if not payload:
        return projection
    return replace(
        projection,
        merge_completed=True,
        merge_result=dict(sorted(payload.items())),
    )


def _snapshot_identity(
    payload: dict[str, object],
) -> tuple[str, str, str] | None:
    snapshot_id = _optional_text(payload, "snapshot_id")
    content_hash = _optional_text(payload, "content_hash")
    immutable_uri = _optional_text(payload, "immutable_uri")
    if None in (snapshot_id, content_hash, immutable_uri):
        return None
    return cast(tuple[str, str, str], (snapshot_id, content_hash, immutable_uri))


def _project_input_snapshot_published(
    projection: RunLedgerReplayProjection,
    entry: RunLedgerEntry,
) -> RunLedgerReplayProjection:
    payload = _details(entry)
    identity = _snapshot_identity(payload)
    if identity is None:
        return projection
    snapshot_id, _, _ = identity
    snapshots_by_id = {
        str(item.get("snapshot_id")): item for item in projection.input_snapshots
    }
    snapshots_by_id[snapshot_id] = dict(sorted(payload.items()))
    return replace(
        projection,
        input_snapshots=tuple(snapshots_by_id[key] for key in sorted(snapshots_by_id)),
    )


_EVENT_PROJECTORS: dict[str, _ProjectionFn] = {
    STAGE_COMPLETED_EVENT: _project_stage_completed,
    COMPOSITE_DEPENDENCY_COMPLETED_EVENT: _project_composite_dependency_completed,
    COMPOSITE_ENRICHER_COMPLETED_EVENT: _project_composite_enricher_completed,
    COMPOSITE_MERGE_COMPLETED_EVENT: _project_composite_merge_completed,
    INPUT_SNAPSHOT_PUBLISHED_EVENT: _project_input_snapshot_published,
}

_PASS_THROUGH_EVENT_TYPES = frozenset(
    {
        MANIFEST_CREATED_EVENT,
        RUN_STARTED_EVENT,
        RUN_SHUTDOWN_EVENT,
        STAGE_STARTED_EVENT,
        ARTIFACT_PUBLISHED_EVENT,
        DQ_POLICY_APPLIED_EVENT,
    }
)

_TERMINAL_STATES = {
    RUN_FINISHED_EVENT: CompositePipelineState.COMPLETED,
    RUN_FAILED_EVENT: CompositePipelineState.FAILED,
}


def _advance_watermark(
    projection: RunLedgerReplayProjection,
    entry: RunLedgerEntry,
) -> RunLedgerReplayProjection:
    return replace(
        projection,
        last_event_id=entry.entry_id,
        last_event_occurred_at=entry.occurred_at,
    )


def _mark_projection_unsupported(
    projection: RunLedgerReplayProjection,
    entry: RunLedgerEntry,
) -> RunLedgerReplayProjection:
    unsupported = {
        *projection.unsupported_replay_entries,
        (entry.entry_id, entry.event_type, entry.stage),
    }
    return replace(
        projection,
        projector_coverage_complete=False,
        unsupported_replay_entries=tuple(sorted(unsupported)),
    )


def _apply_replay_entry(
    projection: RunLedgerReplayProjection,
    entry: RunLedgerEntry,
) -> RunLedgerReplayProjection:
    replayed = _advance_watermark(projection, entry)
    projector = _EVENT_PROJECTORS.get(entry.event_type)
    if projector is not None:
        projected = projector(replayed, entry)
        if projected is replayed and entry.event_type == STAGE_COMPLETED_EVENT:
            return _mark_projection_unsupported(replayed, entry)
        return projected
    terminal_state = _TERMINAL_STATES.get(entry.event_type)
    if terminal_state is None:
        if entry.event_type in _PASS_THROUGH_EVENT_TYPES:
            return replayed
        return _mark_projection_unsupported(replayed, entry)
    return replace(replayed, state=terminal_state)


def project_run_ledger_replay(
    entries: tuple[RunLedgerEntry, ...] | list[RunLedgerEntry],
) -> RunLedgerReplayProjection:
    """Project append-ordered ledger entries into a deterministic replay delta."""
    projection = RunLedgerReplayProjection(replayed_entry_count=len(entries))
    for entry in entries:
        projection = _apply_replay_entry(projection, entry)
    return projection
