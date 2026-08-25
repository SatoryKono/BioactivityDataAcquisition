"""Internal mixins for PipelineRun aggregate behavior."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.aggregates.events import (
    PipelineCompleted,
    PipelineFailed,
    PipelineShutdown,
)
from bioetl.domain.aggregates.pipeline_run_stage_result import (
    PipelineRunState,
    StageResult,
    StageStatus,
)
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.types import JsonDict, RunID, RunType

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent

__all__ = [
    "_PipelineRunAttrs",
    "_PipelineRunLifecycleMixin",
]


class _PipelineRunAttrs:
    """Typed private attributes shared by PipelineRun behavior."""

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

    def __init__(self) -> None:
        """Initialize typed slots for standalone mixin safety."""
        self._run_id = cast(Any, None)
        self._run_type = cast(Any, None)
        self._pipeline_name = ""
        self._status = PipelineRunState.PENDING
        self._stages = []
        self._started_at = None
        self._ended_at = None
        self._events = []
        self._manifest_id = None
        self._metadata = {}


class _PipelineRunLifecycleMixin(_PipelineRunAttrs):
    """State-transition methods for PipelineRun."""

    __slots__ = ()

    def start(self, started_at: datetime) -> None:
        """Start the pipeline run at an explicit timestamp."""
        if self._status != PipelineRunState.PENDING:
            raise InvalidStateError(
                f"Cannot start run in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation="start",
            )
        self._status = PipelineRunState.RUNNING
        self._started_at = started_at

    def record_stage_start(self, stage: str, started_at: datetime) -> None:
        """Record the start of a pipeline stage (compat P2-9 until 2026-06-30)."""
        self._assert_running("record_stage_start")
        self._stages.append(
            StageResult(
                stage=stage,
                status=StageStatus.RUNNING,
                started_at=started_at,
            )
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
        """Record a successful stage (compat P2-9 until 2026-06-30)."""
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
        # Idempotent completion: do not append a second SUCCESS when the
        # stage was already completed and no RUNNING entry remains.
        if self._has_stage_status(stage, StageStatus.SUCCESS):
            return
        self._stages.append(completed)

    def _replace_running_stage(self, stage: str, completed: StageResult) -> bool:
        """Replace the latest RUNNING entry for stage; return True if replaced."""
        for index in range(len(self._stages) - 1, -1, -1):
            current = self._stages[index]
            if current.stage == stage and current.status == StageStatus.RUNNING:
                self._stages[index] = completed
                return True
        return False

    def _has_stage_status(self, stage: str, status: StageStatus) -> bool:
        """Return True when any stage entry matches stage/status."""
        return any(
            existing.stage == stage and existing.status == status
            for existing in self._stages
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
        """Record a failed stage and fail the run (compat P2-9)."""
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
        # Match record_stage_success: replace RUNNING entry when present so a
        # stage does not accumulate both RUNNING and FAILED projections.
        if not self._replace_running_stage(stage, failed):
            # Idempotent failure: do not append a second FAILED when the stage
            # was already failed and no RUNNING entry remains.
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

    def complete(self, completed_at: datetime) -> None:
        """Mark run as COMPLETED if all stages succeeded."""
        self._assert_running("complete")
        self._assert_can_complete()
        ended_at = completed_at
        self._status = PipelineRunState.COMPLETED
        self._ended_at = ended_at

        records_processed = sum(stage.records_processed for stage in self._stages)
        duration_seconds = 0.0
        if self._started_at is not None:
            duration_seconds = (ended_at - self._started_at).total_seconds()

        self._events.append(
            PipelineCompleted(
                occurred_at=ended_at,
                run_id=self._run_id,
                pipeline_name=self._pipeline_name,
                records_processed=records_processed,
                duration_seconds=duration_seconds,
                stages_count=len(self._stages),
            )
        )

    def fail(
        self,
        error: str,
        error_type: str | None = None,
        *,
        failed_at: datetime,
    ) -> None:
        """Mark run as failed without stage-level details."""
        self._assert_running("fail")
        self._status = PipelineRunState.FAILED
        self._ended_at = failed_at
        self._events.append(
            PipelineFailed(
                occurred_at=failed_at,
                run_id=self._run_id,
                pipeline_name=self._pipeline_name,
                failed_stage="unknown",
                error=error,
                error_type=error_type,
            )
        )

    def shutdown(self, shutdown_at: datetime) -> None:
        """Mark the run as gracefully shutdown.

        Args:
            shutdown_at: Explicit shutdown timestamp.
        """
        self._assert_running("shutdown")
        ended_at = shutdown_at
        self._status = PipelineRunState.SHUTDOWN
        self._ended_at = ended_at
        self._events.append(
            PipelineShutdown(
                occurred_at=ended_at,
                run_id=self._run_id,
                pipeline_name=self._pipeline_name,
                records_processed=sum(
                    stage.records_processed for stage in self._stages
                ),
            )
        )

    def _assert_can_complete(self) -> None:
        self._assert_no_failed_stages()
        self._assert_has_recorded_stages()
        self._assert_all_stages_successful()

    def _assert_no_failed_stages(self) -> None:
        failed_stage_names = [
            stage.stage for stage in self._stages if stage.status == StageStatus.FAILED
        ]
        if failed_stage_names:
            raise InvalidStateError(
                "Cannot complete run: "
                f"{len(failed_stage_names)} stages failed: {failed_stage_names}",
                current_state=self._status.value,
                attempted_operation="complete",
            )

    def _assert_has_recorded_stages(self) -> None:
        if not self._stages:
            raise InvalidStateError(
                "Cannot complete run: no stages recorded",
                current_state=self._status.value,
                attempted_operation="complete",
            )

    def _assert_all_stages_successful(self) -> None:
        incomplete_stage_names = [
            f"{stage.stage}:{stage.status.value}"
            for stage in self._stages
            if stage.status != StageStatus.SUCCESS
        ]
        if incomplete_stage_names:
            raise InvalidStateError(
                "Cannot complete run: "
                "all recorded stages must be SUCCESS before terminal completion; "
                f"found {incomplete_stage_names}",
                current_state=self._status.value,
                attempted_operation="complete",
            )

    def _assert_running(self, operation: str) -> None:
        if self._status != PipelineRunState.RUNNING:
            raise InvalidStateError(
                f"Cannot {operation}: run is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation=operation,
            )
