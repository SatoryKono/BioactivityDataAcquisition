"""Stage recording transitions for the PipelineRun aggregate."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.aggregates.events import PipelineFailed
from bioetl.domain.aggregates.pipeline_run_stage_result import (
    PipelineRunState,
    StageResult,
    StageStatus,
    utc_instant,
)
from bioetl.domain.exceptions import InvalidStateError

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent
    from bioetl.domain.types import JsonDict, RunID, RunType


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

    @staticmethod
    def _validate_timestamp(value: datetime) -> datetime:
        return utc_instant(value)

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
