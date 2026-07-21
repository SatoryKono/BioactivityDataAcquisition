"""Internal mixins for PipelineRun aggregate behavior."""

from __future__ import annotations

from datetime import datetime

from bioetl.domain.aggregates._pipeline_run_read_model_mixin import (
    _PipelineRunAttrs,
    _PipelineRunReadModelMixin,
)
from bioetl.domain.aggregates.events import (
    PipelineCompleted,
    PipelineFailed,
    PipelineShutdown,
)
from bioetl.domain.aggregates.pipeline_run_stage_result import StageResult
from bioetl.domain.aggregates.pipeline_run_state import PipelineRunState, StageStatus
from bioetl.domain.exceptions import InvalidStateError

__all__ = [
    "_PipelineRunAttrs",
    "_PipelineRunLifecycleMixin",
    "_PipelineRunReadModelMixin",
]


class _PipelineRunLifecycleMixin(_PipelineRunAttrs):
    """State-transition methods for PipelineRun."""

    __slots__ = ()

    def start(self, started_at: datetime) -> None:
        """Start the pipeline run.

        Args:
            started_at: Explicit start timestamp.
        """
        if self._status != PipelineRunState.PENDING:
            raise InvalidStateError(
                f"Cannot start run in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation="start",
            )
        self._status = PipelineRunState.RUNNING
        self._started_at = started_at

    def record_stage_start(self, stage: str, started_at: datetime) -> None:
        """Record the start of a pipeline stage.

        Compatibility path (P2-9):
            Prefer application.services.PipelineRunLifecycleService for orchestration
            call-sites. Domain aggregate API remains temporarily stable through
            2026-06-30 for migration safety.

        Args:
            stage: Name of the pipeline stage being started (e.g., 'bronze', 'silver').
            started_at: Explicit stage start timestamp.
        """
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
        """Record successful completion of a pipeline stage.

        Compatibility path (P2-9):
            Prefer application.services.PipelineRunLifecycleService for orchestration
            call-sites. Domain aggregate API remains temporarily stable through
            2026-06-30 for migration safety.

        Args:
            stage: Name of the pipeline stage that succeeded.
            result: Optional stage result payload for audit/lineage purposes.
            records_processed: Number of records processed during this stage. Defaults to 0.
            started_at: Explicit stage start timestamp.
            completed_at: Explicit stage completion timestamp.
        """
        self._assert_running("record_stage_success")
        completed = StageResult(
            stage=stage,
            status=StageStatus.SUCCESS,
            started_at=started_at,
            completed_at=completed_at,
            result=result,
            records_processed=records_processed,
        )
        for index in range(len(self._stages) - 1, -1, -1):
            if (
                self._stages[index].stage == stage
                and self._stages[index].status == StageStatus.RUNNING
            ):
                self._stages[index] = completed
                break
        else:
            self._stages.append(completed)

    def record_stage_failure(
        self,
        stage: str,
        error: str | Exception,
        error_type: str | None = None,
        *,
        started_at: datetime,
        completed_at: datetime,
    ) -> None:
        """Record failure of a pipeline stage and fail the run.

        Compatibility path (P2-9):
            Prefer application.services.PipelineRunLifecycleService for orchestration
            call-sites. Domain aggregate API remains temporarily stable through
            2026-06-30 for migration safety.

        Args:
            stage: Name of the pipeline stage that failed.
            error: Error message string or Exception instance describing the failure.
            error_type: Optional error classification (e.g., exception class name).
            started_at: Explicit stage start timestamp.
            completed_at: Explicit failure timestamp.
        """
        self._assert_running("record_stage_failure")
        error_message = str(error) if isinstance(error, Exception) else error
        ended_at = completed_at

        self._stages.append(
            StageResult(
                stage=stage,
                status=StageStatus.FAILED,
                started_at=started_at,
                completed_at=ended_at,
                error=error_message,
                error_type=error_type,
            )
        )
        self._status = PipelineRunState.FAILED
        self._ended_at = ended_at
        self._events.append(
            PipelineFailed(
                occurred_at=ended_at,
                run_id=self._run_id,
                pipeline_name=self._pipeline_name,
                failed_stage=stage,
                error=error_message,
                error_type=error_type,
            )
        )

    def complete(self, completed_at: datetime) -> None:
        """Mark run as COMPLETED if all stages succeeded.

        Args:
            completed_at: Explicit completion timestamp.
        """
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
        """Mark run as failed without stage-level details.

        Args:
            error: Human-readable error description.
            error_type: Optional error classification (e.g., exception class name).
            failed_at: Explicit failure timestamp.
        """
        self._assert_running("fail")
        ended_at = failed_at
        self._status = PipelineRunState.FAILED
        self._ended_at = ended_at
        self._events.append(
            PipelineFailed(
                occurred_at=ended_at,
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
