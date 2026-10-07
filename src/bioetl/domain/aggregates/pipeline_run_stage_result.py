"""Stage-level value objects and run-state enums for pipeline runs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from bioetl.domain.immutability import (
    FrozenDict,
    FrozenList,
    deep_freeze_json,
    deep_thaw_json,
)


class StageStatus(StrEnum):
    """Status of a pipeline stage."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineRunState(StrEnum):
    """Lifecycle state of a pipeline run (PENDING -> RUNNING -> terminal)."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SHUTDOWN = "shutdown"

    def is_terminal(self) -> bool:
        """Check if terminal (no more transitions)."""
        return self in {
            PipelineRunState.COMPLETED,
            PipelineRunState.FAILED,
            PipelineRunState.SHUTDOWN,
        }


def _validate_failed_has_error(status: StageStatus, error: str | None) -> None:
    if status != StageStatus.FAILED:
        return
    if error:
        return
    raise ValueError("Failed stage must have an error message")


def _validate_in_progress_no_completion(
    status: StageStatus,
    completed_at: datetime | None,
) -> None:
    if status not in {StageStatus.PENDING, StageStatus.RUNNING}:
        return
    if completed_at is None:
        return
    raise ValueError(
        f"In-progress stage must not have completed_at timestamp, got status={status.value}"
    )


def _validate_terminal_has_completion(
    status: StageStatus,
    completed_at: datetime | None,
) -> None:
    if status not in {StageStatus.SUCCESS, StageStatus.FAILED}:
        return
    if completed_at:
        return
    raise ValueError(
        f"Completed/Failed stage must have completed_at timestamp, got status={status.value}"
    )


def utc_instant(value: datetime) -> datetime:
    """Compare aware instants without changing their identity representation."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _validate_completion_order(
    completed_at: datetime | None,
    started_at: datetime,
) -> None:
    start = utc_instant(started_at)
    if completed_at is None:
        return
    if utc_instant(completed_at) >= start:
        return
    raise ValueError(
        "completed_at cannot be earlier than started_at: "
        f"started_at={started_at!s}, completed_at={completed_at!s}"
    )


def _validate_stage_result(
    stage: str,
    status: StageStatus,
    error: str | None,
    completed_at: datetime | None,
    records_processed: int,
    started_at: datetime,
) -> None:
    if not stage:
        raise ValueError("Stage name cannot be empty")
    _validate_failed_has_error(status, error)
    _validate_in_progress_no_completion(status, completed_at)
    _validate_terminal_has_completion(status, completed_at)
    _validate_completion_order(completed_at, started_at)
    if records_processed < 0:
        raise ValueError(f"records_processed cannot be negative: {records_processed}")


@dataclass(frozen=True, slots=True)
class StageResult:
    """Stage evidence with detached results.

    JSON collections are exposed as immutable snapshots. Other copyable domain
    values retain their type and are defensively copied on construction/access.
    """

    stage: str
    status: StageStatus
    started_at: datetime
    completed_at: datetime | None = None
    result: object = None
    error: str | None = None
    error_type: str | None = None
    records_processed: int = 0

    def __post_init__(self) -> None:
        """Validate stage result invariants."""
        _validate_stage_result(
            self.stage,
            self.status,
            self.error,
            self.completed_at,
            self.records_processed,
            self.started_at,
        )
        value = object.__getattribute__(self, "result")
        snapshot = (
            deep_thaw_json(value)
            if isinstance(value, (FrozenDict, FrozenList))
            else deepcopy(value)
        )
        object.__setattr__(self, "result", snapshot)

    def __getattribute__(self, name: str) -> object:
        """Never expose a stored result alias, including complex value objects."""
        value = object.__getattribute__(self, name)
        if name != "result":
            return value
        # Dataclass copying/pickling can restore the accessor's frozen snapshot.
        # Thaw it first so nested copyable values cannot become stored aliases.
        if isinstance(value, (FrozenDict, FrozenList)):
            value = deep_thaw_json(value)
        return deep_freeze_json(value)

    @property
    def duration_seconds(self) -> float | None:
        """Calculate stage duration in seconds for valid completions only."""
        if self.completed_at is None:
            return None
        if self.status in {StageStatus.PENDING, StageStatus.RUNNING}:
            return None
        duration = (
            utc_instant(self.completed_at) - utc_instant(self.started_at)
        ).total_seconds()
        if duration < 0:
            return None
        return duration

    def with_success(
        self,
        completed_at: datetime,
        result: object = None,
        records_processed: int = 0,
    ) -> StageResult:
        """Return a SUCCESS copy of this stage result."""
        return StageResult(
            stage=self.stage,
            status=StageStatus.SUCCESS,
            started_at=self.started_at,
            completed_at=completed_at,
            result=result,
            records_processed=records_processed,
        )

    def with_failure(
        self,
        completed_at: datetime,
        error: str,
        error_type: str | None = None,
    ) -> StageResult:
        """Return a FAILED copy of this stage result."""
        return StageResult(
            stage=self.stage,
            status=StageStatus.FAILED,
            started_at=self.started_at,
            completed_at=completed_at,
            error=error,
            error_type=error_type,
            records_processed=self.records_processed,
        )


__all__ = ["PipelineRunState", "StageResult", "StageStatus", "utc_instant"]
