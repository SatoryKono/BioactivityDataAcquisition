"""Result assembly service for dependency execution outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.domain.composite import DependencyConfig
from bioetl.domain.composite.result import DependencyResult
from bioetl.domain.ports import ExecutionMetricsReadablePort, LoggerPort

__all__ = ["DependencyResultService"]


def _duration_seconds(started_at: datetime, completed_at: datetime) -> float:
    """Calculate wall-clock duration in seconds."""
    return (completed_at - started_at).total_seconds()


def _extract_runner_metrics(runner: ExecutionMetricsReadablePort) -> tuple[int, int]:
    """Extract available row counters from runner public metrics view."""
    metrics = runner.execution_metrics
    return (
        int(metrics["records_fetched"]),
        int(metrics["records_silver"]),
    )


@dataclass(frozen=True, slots=True)
class DependencyResultService:
    """Assembles dependency execution outcomes into stable result objects."""

    logger: LoggerPort

    def build_timeout_result(
        self,
        *,
        dependency: DependencyConfig,
        started_at: datetime,
        completed_at: datetime,
        duration_seconds: float,
    ) -> DependencyResult:
        """Build timeout result and emit warning log."""
        self.logger.warning(
            "Dependency timed out",
            dependency=dependency.pipeline,
            timeout_seconds=dependency.timeout_seconds,
            duration_seconds=duration_seconds,
        )
        return DependencyResult.timeout(
            pipeline_name=dependency.pipeline,
            timeout_seconds=dependency.timeout_seconds,
            duration_seconds=duration_seconds,
            started_at=started_at,
            completed_at=completed_at,
        )

    def build_failed_result(
        self,
        *,
        dependency: DependencyConfig,
        error: Exception,
        started_at: datetime,
        completed_at: datetime,
        duration_seconds: float,
    ) -> DependencyResult:
        """Build failed result and emit required/optional failure log."""
        log_method = self.logger.error if dependency.required else self.logger.warning
        log_method(
            "Required dependency failed"
            if dependency.required
            else "Optional dependency failed",
            dependency=dependency.pipeline,
            error=str(error),
            error_type=type(error).__name__,
            required=dependency.required,
            duration_seconds=duration_seconds,
        )
        return DependencyResult.failed(
            pipeline_name=dependency.pipeline,
            error_message=str(error),
            duration_seconds=duration_seconds,
            started_at=started_at,
            completed_at=completed_at,
        )

    def build_success_result(
        self,
        *,
        dependency: DependencyConfig,
        runner: ExecutionMetricsReadablePort,
        started_at: datetime,
        completed_at: datetime,
        duration_seconds: float,
    ) -> DependencyResult:
        """Build success result and emit completion log."""
        records_extracted, records_silver = _extract_runner_metrics(runner)
        self.logger.info(
            "Dependency completed",
            dependency=dependency.pipeline,
            records_extracted=records_extracted,
            records_silver=records_silver,
            duration_seconds=duration_seconds,
        )
        return DependencyResult.success(
            pipeline_name=dependency.pipeline,
            records_extracted=records_extracted,
            records_silver=records_silver,
            duration_seconds=duration_seconds,
            started_at=started_at,
            completed_at=completed_at,
        )
