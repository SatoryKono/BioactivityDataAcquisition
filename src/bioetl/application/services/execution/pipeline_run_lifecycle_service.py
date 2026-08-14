"""Application-level orchestration service for PipelineRun lifecycle.

Migration note (P2-9):
    Application/composition should prefer this service for PipelineRun lifecycle
    orchestration. Domain aggregate lifecycle methods remain as the domain API
    surface and are not scheduled for removal by a calendar sunset in this note.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.domain.ports import ClockPort
    from bioetl.domain.types import JsonDict


class _PipelineRunLifecycleProtocol(Protocol):
    """Minimal lifecycle surface required from a PipelineRun-like aggregate."""

    def start(self, started_at: datetime) -> None: ...

    def record_stage_start(self, *, stage: str, started_at: datetime) -> None: ...

    def record_stage_success(
        self,
        *,
        stage: str,
        result: JsonDict | None,
        records_processed: int,
        started_at: datetime,
        completed_at: datetime,
    ) -> None: ...

    def record_stage_failure(
        self,
        *,
        stage: str,
        error: str | Exception,
        error_type: str | None,
        started_at: datetime,
        completed_at: datetime,
    ) -> None: ...

    def complete(self, *, completed_at: datetime) -> None: ...

    def fail(
        self,
        *,
        error: str,
        error_type: str | None,
        failed_at: datetime,
    ) -> None: ...

    def shutdown(self, *, shutdown_at: datetime) -> None: ...


@dataclass(slots=True)
class PipelineRunLifecycleService:
    """Coordinate PipelineRun lifecycle transitions in application layer."""

    clock: ClockPort

    def start_run(
        self,
        run: _PipelineRunLifecycleProtocol,
        started_at: datetime | None = None,
    ) -> None:
        """Start pipeline run.

        Args:
            run: PipelineRun aggregate to transition to the running state.
            started_at: Optional explicit start timestamp. Defaults to now (UTC).
        """
        run.start(started_at or self.clock.now())

    def stage_started(
        self,
        run: _PipelineRunLifecycleProtocol,
        stage: str,
        started_at: datetime | None = None,
    ) -> None:
        """Record stage start transition.

        Args:
            run: PipelineRun aggregate to record the stage start on.
            stage: Stage name identifier (e.g. 'bronze', 'silver', 'gold').
            started_at: Optional explicit start timestamp. Defaults to now (UTC).
        """
        run.record_stage_start(stage=stage, started_at=started_at or self.clock.now())

    def stage_succeeded(
        self,
        run: _PipelineRunLifecycleProtocol,
        stage: str,
        *,
        result: JsonDict | None = None,  # Any: stage payload can vary
        records_processed: int = 0,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Record successful stage completion.

        Args:
            run: PipelineRun aggregate to record the stage success on.
            stage: Stage name identifier (e.g. 'bronze', 'silver', 'gold').
            result: Optional dict of stage output metadata or statistics.
            records_processed: Number of records written in this stage.
            started_at: Optional stage start timestamp. Defaults to now (UTC).
            completed_at: Optional stage completion timestamp. Defaults to now (UTC).
        """
        now = self.clock.now()
        run.record_stage_success(
            stage=stage,
            result=result,
            records_processed=records_processed,
            started_at=started_at or now,
            completed_at=completed_at or now,
        )

    def stage_failed(
        self,
        run: _PipelineRunLifecycleProtocol,
        stage: str,
        *,
        error: str | Exception,
        error_type: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Record failed stage transition.

        Args:
            run: PipelineRun aggregate to record the stage failure on.
            stage: Stage name identifier (e.g. 'bronze', 'silver', 'gold').
            error: Error message string or Exception that caused the failure.
            error_type: Optional error class name string for categorization.
            started_at: Optional stage start timestamp. Defaults to now (UTC).
            completed_at: Optional stage failure timestamp. Defaults to now (UTC).
        """
        now = self.clock.now()
        run.record_stage_failure(
            stage=stage,
            error=error,
            error_type=error_type,
            started_at=started_at or now,
            completed_at=completed_at or now,
        )

    def complete_run(
        self,
        run: _PipelineRunLifecycleProtocol,
        completed_at: datetime | None = None,
    ) -> None:
        """Complete run when all stage invariants are satisfied.

        Args:
            run: PipelineRun aggregate to transition to the completed state.
            completed_at: Optional explicit completion timestamp. Defaults to now (UTC).
        """
        run.complete(completed_at=completed_at or self.clock.now())

    def fail_run(
        self,
        run: _PipelineRunLifecycleProtocol,
        *,
        error: str,
        error_type: str | None = None,
        failed_at: datetime | None = None,
    ) -> None:
        """Fail run with pipeline-level failure details.

        Args:
            run: PipelineRun aggregate to transition to the failed state.
            error: Human-readable error description for the pipeline failure.
            error_type: Optional error class name string for categorization.
            failed_at: Optional explicit failure timestamp. Defaults to now (UTC).
        """
        run.fail(
            error=error,
            error_type=error_type,
            failed_at=failed_at or self.clock.now(),
        )

    def shutdown_run(
        self,
        run: _PipelineRunLifecycleProtocol,
        shutdown_at: datetime | None = None,
    ) -> None:
        """Mark run as gracefully shut down.

        Args:
            run: PipelineRun aggregate to transition to the shutdown state.
            shutdown_at: Optional explicit shutdown timestamp. Defaults to now (UTC).
        """
        run.shutdown(shutdown_at=shutdown_at or self.clock.now())


__all__ = ["PipelineRunLifecycleService"]
