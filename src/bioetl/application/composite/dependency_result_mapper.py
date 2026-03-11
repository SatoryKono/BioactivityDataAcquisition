"""Result mapping helpers for dependency execution outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.domain.composite.result import DependencyResult

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.composite.config import DependencyConfig
    from bioetl.domain.ports import LoggerPort

__all__ = ["DependencyResultMapper"]


def _duration_seconds(started_at: datetime, completed_at: datetime) -> float:
    """Calculate wall-clock duration in seconds."""
    return (completed_at - started_at).total_seconds()


def _extract_runner_metrics(runner: PipelineRunner) -> tuple[int, int]:
    """Extract available row counters from runner public metrics view."""
    metrics = getattr(runner, "execution_metrics", None)
    if not isinstance(metrics, dict):
        return 0, 0
    return (
        int(metrics.get("records_fetched", 0)),
        int(metrics.get("records_silver", 0)),
    )


@dataclass(frozen=True, slots=True)
class DependencyResultMapper:
    """Maps dependency execution outcomes into stable result objects."""

    logger: LoggerPort

    def build_timeout_result(
        self,
        *,
        dependency: DependencyConfig,
        started_at: datetime,
    ) -> DependencyResult:
        """Build timeout result and emit warning log."""
        self.logger.warning(
            "Dependency timed out",
            dependency=dependency.pipeline,
            timeout_seconds=dependency.timeout_seconds,
            duration_seconds=_duration_seconds(
                started_at=started_at,
                completed_at=datetime.now(tz=UTC),
            ),
        )
        return DependencyResult.timeout(
            pipeline_name=dependency.pipeline,
            timeout_seconds=dependency.timeout_seconds,
        )

    def build_failed_result(
        self,
        *,
        dependency: DependencyConfig,
        error: Exception,
        started_at: datetime,
    ) -> DependencyResult:
        """Build failed result and emit required/optional failure log."""
        duration = _duration_seconds(
            started_at=started_at,
            completed_at=datetime.now(tz=UTC),
        )
        log_method = self.logger.error if dependency.required else self.logger.warning
        log_method(
            "Required dependency failed"
            if dependency.required
            else "Optional dependency failed",
            dependency=dependency.pipeline,
            error=str(error),
            error_type=type(error).__name__,
            required=dependency.required,
            duration_seconds=duration,
        )
        return DependencyResult.failed(
            pipeline_name=dependency.pipeline,
            error_message=str(error),
            duration_seconds=duration,
        )

    def build_success_result(
        self,
        *,
        dependency: DependencyConfig,
        runner: PipelineRunner,
        started_at: datetime,
        completed_at: datetime,
    ) -> DependencyResult:
        """Build success result and emit completion log."""
        duration = _duration_seconds(started_at=started_at, completed_at=completed_at)
        records_extracted, records_silver = _extract_runner_metrics(runner)
        self.logger.info(
            "Dependency completed",
            dependency=dependency.pipeline,
            records_extracted=records_extracted,
            records_silver=records_silver,
            duration_seconds=duration,
        )
        return DependencyResult.success(
            pipeline_name=dependency.pipeline,
            records_extracted=records_extracted,
            records_silver=records_silver,
            duration_seconds=duration,
            started_at=started_at,
            completed_at=completed_at,
        )
