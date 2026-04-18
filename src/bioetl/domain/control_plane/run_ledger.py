"""Control-plane run ledger models and deterministic replay helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime
from typing import TypedDict, cast
from uuid import UUID

from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.control_plane._run_ledger_event_family import (
    infer_ledger_event_family,
)
from bioetl.domain.control_plane._run_ledger_serialization import (
    load_details,
    load_metrics_snapshot,
    load_optional_str,
    normalize_ledger_value,
)
from bioetl.domain.events import ORDINARY_PIPELINE_STAGE_NAMES
from bioetl.domain.types import RunID

__all__ = [
    "ARTIFACT_PUBLISHED_EVENT",
    "CANONICAL_RUN_LEDGER_STAGE_NAMES",
    "COMPOSITE_RUN_LEDGER_STAGE_NAMES",
    "DQ_POLICY_APPLIED_EVENT",
    "MANIFEST_CREATED_EVENT",
    "ORDINARY_RUN_LEDGER_STAGE_NAMES",
    "RUN_FAILED_EVENT",
    "RUN_FINISHED_EVENT",
    "RUN_LEDGER_BASELINE_EVENT_TYPES",
    "RUN_LEDGER_STAGE_EVENT_TYPES",
    "RUN_SHUTDOWN_EVENT",
    "RUN_STARTED_EVENT",
    "STAGE_COMPLETED_EVENT",
    "STAGE_STARTED_EVENT",
    "RunLedgerEntry",
    "RunLedgerReplayProjection",
    "canonicalize_run_ledger_stage_name",
    "infer_ledger_event_family",
    "project_run_ledger_replay",
    "slice_ledger_entries_after",
]

MANIFEST_CREATED_EVENT = "manifest_created"
RUN_STARTED_EVENT = "run_started"
RUN_FINISHED_EVENT = "run_finished"
RUN_FAILED_EVENT = "run_failed"
RUN_SHUTDOWN_EVENT = "run_shutdown"
STAGE_STARTED_EVENT = "stage_started"
STAGE_COMPLETED_EVENT = "stage_completed"
ARTIFACT_PUBLISHED_EVENT = "artifact_published"
DQ_POLICY_APPLIED_EVENT = "dq_policy_applied"

RUN_LEDGER_BASELINE_EVENT_TYPES: tuple[str, ...] = (
    MANIFEST_CREATED_EVENT,
    RUN_STARTED_EVENT,
    STAGE_STARTED_EVENT,
    STAGE_COMPLETED_EVENT,
    ARTIFACT_PUBLISHED_EVENT,
    RUN_FINISHED_EVENT,
    RUN_FAILED_EVENT,
    RUN_SHUTDOWN_EVENT,
    DQ_POLICY_APPLIED_EVENT,
)

RUN_LEDGER_STAGE_EVENT_TYPES: frozenset[str] = frozenset(
    {STAGE_STARTED_EVENT, STAGE_COMPLETED_EVENT}
)

ORDINARY_RUN_LEDGER_STAGE_NAMES: tuple[str, ...] = ORDINARY_PIPELINE_STAGE_NAMES
COMPOSITE_RUN_LEDGER_STAGE_NAMES: tuple[str, ...] = (
    "seed",
    "dependencies",
    "enrichment",
    "merge",
)
CANONICAL_RUN_LEDGER_STAGE_NAMES: tuple[str, ...] = (
    *ORDINARY_RUN_LEDGER_STAGE_NAMES,
    *COMPOSITE_RUN_LEDGER_STAGE_NAMES,
)
_CANONICAL_RUN_LEDGER_STAGE_NAME_SET = frozenset(CANONICAL_RUN_LEDGER_STAGE_NAMES)


def canonicalize_run_ledger_stage_name(stage: str) -> str:
    """Normalize and validate canonical pipeline stage names for ledger events."""
    normalized_stage = stage.strip().lower()
    if normalized_stage not in _CANONICAL_RUN_LEDGER_STAGE_NAME_SET:
        valid_stages = ", ".join(CANONICAL_RUN_LEDGER_STAGE_NAMES)
        raise ValueError(
            f"Unsupported run-ledger stage {stage!r}; expected one of: {valid_stages}"
        )
    return normalized_stage


def _normalize_run_ledger_stage(event_type: str, stage: str | None) -> str | None:
    """Normalize canonical pipeline stages without touching non-pipeline vocabularies."""
    if stage is None:
        return None
    if event_type not in RUN_LEDGER_STAGE_EVENT_TYPES:
        return stage
    return canonicalize_run_ledger_stage_name(stage)


def slice_ledger_entries_after(
    entries: list[RunLedgerEntry],
    after_entry_id: str | None,
) -> tuple[RunLedgerEntry, ...]:
    """Return the append-ordered suffix strictly after one watermark entry."""
    if after_entry_id is None:
        return tuple(entries)
    for index, entry in enumerate(entries):
        if entry.entry_id == after_entry_id:
            return tuple(entries[index + 1 :])
    raise ValueError(
        f"Ledger watermark entry_id {after_entry_id!r} was not found in append order"
    )


@dataclass(frozen=True, slots=True)
class RunLedgerReplayProjection:
    """Deterministic replay delta for durable lifecycle milestones only."""

    state: CompositePipelineState | None = None
    seed_completed: bool | None = None
    merge_completed: bool | None = None
    last_event_id: str | None = None
    last_event_occurred_at: datetime | None = None
    replayed_entry_count: int = 0


class _StageCompletionUpdate(TypedDict, total=False):
    state: CompositePipelineState
    seed_completed: bool
    merge_completed: bool


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
    stage = (entry.stage or "").strip().lower()
    update = _STAGE_COMPLETION_UPDATES.get(stage)
    if update is None:
        return projection
    return cast(RunLedgerReplayProjection, replace(projection, **update))


def _apply_replay_entry(
    projection: RunLedgerReplayProjection,
    entry: RunLedgerEntry,
) -> RunLedgerReplayProjection:
    replayed = cast(
        RunLedgerReplayProjection,
        replace(
            projection,
            last_event_id=entry.entry_id,
            last_event_occurred_at=entry.occurred_at,
        ),
    )
    if entry.event_type == STAGE_COMPLETED_EVENT:
        return _project_stage_completed(replayed, entry)
    if entry.event_type == RUN_FINISHED_EVENT:
        return cast(
            RunLedgerReplayProjection,
            replace(replayed, state=CompositePipelineState.COMPLETED),
        )
    if entry.event_type == RUN_FAILED_EVENT:
        return cast(
            RunLedgerReplayProjection,
            replace(replayed, state=CompositePipelineState.FAILED),
        )
    return replayed


def project_run_ledger_replay(
    entries: tuple[RunLedgerEntry, ...] | list[RunLedgerEntry],
) -> RunLedgerReplayProjection:
    """Project append-ordered ledger entries into a deterministic replay delta."""
    projection = RunLedgerReplayProjection(replayed_entry_count=len(entries))
    for entry in entries:
        projection = _apply_replay_entry(projection, entry)
    return projection


@dataclass(frozen=True, slots=True)
class RunLedgerEntry:
    """Append-only control-plane event linked to one manifest/run pair."""

    entry_id: str
    manifest_id: str
    run_id: RunID
    event_type: str
    occurred_at: datetime
    event_family: str | None = None
    status: str | None = None
    stage: str | None = None
    message: str | None = None
    error_type: str | None = None
    dataset_ref: str | None = None
    lineage_fragment_id: str | None = None
    metrics_snapshot: dict[str, int] | None = None
    details: dict[str, object] | None = None

    def __post_init__(self) -> None:
        """Ensure taxonomy and event-type payload are canonicalized."""
        normalized_event_type = str(self.event_type).strip().lower()
        if not normalized_event_type:
            normalized_event_type = "unknown_event"
        object.__setattr__(self, "event_type", normalized_event_type)
        object.__setattr__(
            self,
            "stage",
            _normalize_run_ledger_stage(normalized_event_type, self.stage),
        )
        if self.event_family is None:
            object.__setattr__(
                self,
                "event_family",
                infer_ledger_event_family(normalized_event_type),
            )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable ledger payload."""
        return {
            key: normalize_ledger_value(value) for key, value in asdict(self).items()
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> RunLedgerEntry:
        """Hydrate a ledger entry from serialized JSON payload."""
        return cls(
            entry_id=str(payload["entry_id"]),
            manifest_id=str(payload["manifest_id"]),
            run_id=RunID(UUID(str(payload["run_id"]))),
            event_type=str(payload["event_type"]),
            event_family=load_optional_str(payload, "event_family"),
            occurred_at=datetime.fromisoformat(str(payload["occurred_at"])),
            status=load_optional_str(payload, "status"),
            stage=None if payload.get("stage") is None else str(payload["stage"]),
            message=load_optional_str(payload, "message"),
            error_type=load_optional_str(payload, "error_type"),
            dataset_ref=load_optional_str(payload, "dataset_ref"),
            lineage_fragment_id=load_optional_str(payload, "lineage_fragment_id"),
            metrics_snapshot=load_metrics_snapshot(payload.get("metrics_snapshot")),
            details=load_details(payload.get("details")),
        )
