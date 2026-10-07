"""Stage-level value objects and run-state enums for pipeline runs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from bioetl.domain.aggregates.events import PipelineFailed
from bioetl.domain.context_time import utc_instant, validate_completion_order
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.immutability import (
    FrozenDict,
    FrozenList,
    deep_freeze_json,
    deep_thaw_json,
)

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent
    from bioetl.domain.types import RunID


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
    if status == StageStatus.FAILED and not error:
        raise ValueError("Failed stage must have an error message")


def _validate_in_progress_no_completion(
    status: StageStatus,
    completed_at: datetime | None,
) -> None:
    if (
        status in {StageStatus.PENDING, StageStatus.RUNNING}
        and completed_at is not None
    ):
        raise ValueError(
            f"In-progress stage must not have completed_at timestamp, got status={status.value}"
        )


def _validate_terminal_has_completion(
    status: StageStatus,
    completed_at: datetime | None,
) -> None:
    if status in {StageStatus.SUCCESS, StageStatus.FAILED} and not completed_at:
        raise ValueError(
            f"Completed/Failed stage must have completed_at timestamp, got status={status.value}"
        )


def _validate_stage_result(value: StageResult) -> None:
    if not value.stage:
        raise ValueError("Stage name cannot be empty")
    _validate_failed_has_error(value.status, value.error)
    _validate_in_progress_no_completion(value.status, value.completed_at)
    _validate_terminal_has_completion(value.status, value.completed_at)
    validate_completion_order(value.completed_at, value.started_at)
    if value.records_processed < 0:
        raise ValueError(
            f"records_processed cannot be negative: {value.records_processed}"
        )


@dataclass(frozen=True, slots=True)
class StageResult:
    """Stage evidence with immutable JSON collections and detached domain values.

    Other copyable values retain their type via construction/access copies.
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
        _validate_stage_result(self)
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
        # Thaw restored frozen snapshots to avoid aliases to nested copyable values.
        if isinstance(value, (FrozenDict, FrozenList)):
            value = deep_thaw_json(value)
        try:
            return deep_freeze_json(value)
        except TypeError:
            return deepcopy(value)

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


class _PipelineRunStageMixin:
    """Stage transitions sharing PipelineRun's slot layout and annotations."""

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
    _pipeline_name: str
    _status: PipelineRunState
    _stages: list[StageResult]
    _started_at: datetime | None
    _ended_at: datetime | None
    _events: list[DomainEvent]

    _validate_timestamp = staticmethod(utc_instant)

    def _validate_end_timestamp(self, value: datetime) -> datetime:
        end = utc_instant(value)
        if self._started_at is not None and end < utc_instant(self._started_at):
            raise ValueError("end timestamp cannot be earlier than run started_at")
        return end

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
        self._validate_end_timestamp(completed_at)
        if not self._has_stage_status(
            stage, StageStatus.RUNNING
        ) and self._has_stage_status(stage, StageStatus.FAILED):
            return
        event = PipelineFailed(
            occurred_at=completed_at,
            run_id=self._run_id,
            pipeline_name=self._pipeline_name,
            failed_stage=stage,
            error=error_message,
            error_type=error_type,
        )
        if not self._replace_running_stage(stage, failed):
            self._stages.append(failed)
        self._status = PipelineRunState.FAILED
        self._ended_at = completed_at
        self._events.append(event)

    def _assert_running(self, operation: str) -> None:
        if self._status != PipelineRunState.RUNNING:
            raise InvalidStateError(
                f"Cannot {operation}: run is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation=operation,
            )


__all__ = ["PipelineRunState", "StageResult", "StageStatus", "utc_instant"]
