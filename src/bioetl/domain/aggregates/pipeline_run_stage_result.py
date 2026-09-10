"""Stage-level value objects and run-state enums for pipeline runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from bioetl.domain.aggregates.events import PipelineFailed
from bioetl.domain.exceptions import InvalidStateError

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent
    from bioetl.domain.types import JsonDict, RunID, RunType


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


def _validate_completion_order(
    completed_at: datetime | None,
    started_at: datetime,
) -> None:
    if completed_at is None:
        return
    if completed_at >= started_at:
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
    """Immutable value object representing the result of a pipeline stage."""

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

    @property
    def duration_seconds(self) -> float | None:
        """Calculate stage duration in seconds for valid completions only."""
        if self.completed_at is None:
            return None
        if self.status in {StageStatus.PENDING, StageStatus.RUNNING}:
            return None
        duration = (self.completed_at - self.started_at).total_seconds()
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


class _PipelineRunStageMixin:
    """Stage recording behavior for PipelineRun.

    Slots and annotations live on this class so mypy sees mixin methods as
    mutating the same instance layout as ``PipelineRun``.
    """

    __slots__ = (
        "_ended_at",
        "_events",
        "_manifest_id",
        "_metadata",
        "_pipeline_name",
        "_run_id",
        "_run_type",
        "_stages",
        "_started_at",
        "_status",
    )
    _run_id: RunID
    _run_type: RunType
    _pipeline_name: str
    _status: PipelineRunState
    _stages: list[StageResult]
    _started_at: datetime | None
    _ended_at: datetime | None
    _events: list[DomainEvent]
    _manifest_id: str | None
    _metadata: JsonDict

    def record_stage_start(self, stage: str, started_at: datetime) -> None:
        """Record the start of a pipeline stage."""
        self._assert_running("record_stage_start")
        self._stages.append(
            StageResult(stage=stage, status=StageStatus.RUNNING, started_at=started_at)
        )

    def record_stage_success(
        self,
        stage: str,
        result: object = None,
        records_processed: int = 0,
        *,
        started_at: datetime,
        completed_at: datetime,
    ) -> None:
        """Record a successful stage."""
        self._assert_running("record_stage_success")
        completed = StageResult(
            stage=stage,
            status=StageStatus.SUCCESS,
            started_at=started_at,
            completed_at=completed_at,
            result=result,
            records_processed=records_processed,
        )
        if self._replace_running_stage(stage, completed):
            return
        if self._has_stage_status(stage, StageStatus.SUCCESS):
            return
        self._stages.append(completed)

    def _replace_running_stage(self, stage: str, completed: StageResult) -> bool:
        for index in range(len(self._stages) - 1, -1, -1):
            current = self._stages[index]
            if current.stage == stage and current.status == StageStatus.RUNNING:
                self._stages[index] = completed
                return True
        return False

    def _has_stage_status(self, stage: str, status: StageStatus) -> bool:
        return any(
            item.stage == stage and item.status == status for item in self._stages
        )

    def record_stage_failure(
        self,
        stage: str,
        error: str | Exception,
        error_type: str | None = None,
        *,
        started_at: datetime,
        completed_at: datetime,
    ) -> None:
        """Record a failed stage and fail the run."""
        self._assert_running("record_stage_failure")
        error_message = str(error) if isinstance(error, Exception) else error
        failed = StageResult(
            stage=stage,
            status=StageStatus.FAILED,
            started_at=started_at,
            completed_at=completed_at,
            error=error_message,
            error_type=error_type,
        )
        if not self._replace_running_stage(stage, failed):
            if self._has_stage_status(stage, StageStatus.FAILED):
                return
            self._stages.append(failed)
        self._status = PipelineRunState.FAILED
        self._ended_at = completed_at
        self._events.append(
            PipelineFailed(
                occurred_at=completed_at,
                run_id=self._run_id,
                pipeline_name=self._pipeline_name,
                failed_stage=stage,
                error=error_message,
                error_type=error_type,
            )
        )

    def _assert_running(self, operation: str) -> None:
        if self._status != PipelineRunState.RUNNING:
            raise InvalidStateError(
                f"Cannot {operation}: run is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation=operation,
            )


__all__ = ["PipelineRunState", "StageResult", "StageStatus"]
