"""Application-level orchestration service for PipelineRun lifecycle.

Migration note (P2-9):
    Domain aggregate methods remain for compatibility, but application/composition
    should prefer this service for lifecycle orchestration. Legacy direct
    orchestration from domain call-sites is targeted for removal by 2026-06-30.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.domain.aggregates.pipeline_run import PipelineRun

if TYPE_CHECKING:
    from bioetl.domain.types import JsonDict


@dataclass(slots=True)
class PipelineRunLifecycleService:
    """Coordinate PipelineRun lifecycle transitions in application layer."""

    def start_run(self, run: PipelineRun, started_at: datetime | None = None) -> None:
        """Start pipeline run."""
        run.start(started_at or datetime.now(UTC))

    def stage_started(
        self,
        run: PipelineRun,
        stage: str,
        started_at: datetime | None = None,
    ) -> None:
        """Record stage start transition."""
        run.record_stage_start(stage=stage, started_at=started_at or datetime.now(UTC))

    def stage_succeeded(
        self,
        run: PipelineRun,
        stage: str,
        *,
        result: JsonDict | None = None,  # Any: stage payload can vary
        records_processed: int = 0,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Record successful stage completion."""
        now = datetime.now(UTC)
        run.record_stage_success(
            stage=stage,
            result=result,
            records_processed=records_processed,
            started_at=started_at or now,
            completed_at=completed_at or now,
        )

    def stage_failed(
        self,
        run: PipelineRun,
        stage: str,
        *,
        error: str | Exception,
        error_type: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Record failed stage transition."""
        now = datetime.now(UTC)
        run.record_stage_failure(
            stage=stage,
            error=error,
            error_type=error_type,
            started_at=started_at or now,
            completed_at=completed_at or now,
        )

    def complete_run(
        self,
        run: PipelineRun,
        completed_at: datetime | None = None,
    ) -> None:
        """Complete run when all stage invariants are satisfied."""
        run.complete(completed_at=completed_at or datetime.now(UTC))

    def fail_run(
        self,
        run: PipelineRun,
        *,
        error: str,
        error_type: str | None = None,
        failed_at: datetime | None = None,
    ) -> None:
        """Fail run with pipeline-level failure details."""
        run.fail(
            error=error,
            error_type=error_type,
            failed_at=failed_at or datetime.now(UTC),
        )

    def shutdown_run(
        self,
        run: PipelineRun,
        shutdown_at: datetime | None = None,
    ) -> None:
        """Mark run as gracefully shut down."""
        run.shutdown(shutdown_at=shutdown_at or datetime.now(UTC))


__all__ = ["PipelineRunLifecycleService"]
