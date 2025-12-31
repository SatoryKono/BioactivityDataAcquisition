"""Postrun Service for post-execution operations.

Application Service that handles post-pipeline execution tasks:
- Data quality checks (delegated to DataQualityService)
- VACUUM operations (delegated to MedallionLifecycleService)
- Tracer cleanup

Extracted from PipelineRunner to follow Single Responsibility Principle.
DQ logic further extracted to DataQualityService (SRP refactoring).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bioetl.application.services.data_quality_service import DataQualityService
from bioetl.application.services.medallion_lifecycle import VacuumResult
from bioetl.domain.value_objects.dq_result import DQResult, DQStatus

if TYPE_CHECKING:
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort


@runtime_checkable
class ExecutorMetricsProtocol(Protocol):
    """Protocol for executors providing batch metrics.

    Both PipelineExecutor and BatchExecutor implement this protocol.
    """

    records_fetched: int
    records_bronze: int
    records_silver: int
    records_gold: int
    records_quarantined: int


@dataclass(frozen=True, slots=True)
class PostrunResult:
    """Combined result of all post-run operations.

    Attributes:
        dq: Data quality evaluation result.
        vacuum: VACUUM operation result.
    """

    dq: DQResult
    vacuum: VacuumResult


class PostrunService:
    """Handles post-execution operations.

    Responsibilities:
    - Orchestrating DQ checks via DataQualityService
    - VACUUM operations via MedallionLifecycleService
    - Tracer cleanup

    Attributes:
        _config: Pipeline configuration.
        _runtime: Runtime configuration.
        _dq_service: Data quality service for DQ checks.
        _lifecycle_service: Medallion lifecycle service for VACUUM.
        _metrics: Optional metrics port.
        _logger: Structured logger.
    """

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        dq_service: DataQualityService,
        lifecycle_service: MedallionLifecycleService,
        metrics: MetricsPort | None,
        logger: LoggerPort,
    ) -> None:
        """Initialize postrun service.

        Args:
            config: Pipeline configuration.
            runtime: Runtime configuration.
            dq_service: Data quality service for DQ checks.
            lifecycle_service: Medallion lifecycle service for VACUUM.
            metrics: Optional metrics port.
            logger: Structured logger.
        """
        self._config = config
        self._runtime = runtime
        self._dq_service = dq_service
        self._lifecycle_service = lifecycle_service
        self._metrics = metrics
        self._logger = logger

    async def run(
        self,
        executor: ExecutorMetricsProtocol,
    ) -> PostrunResult:
        """Run all post-execution operations.

        Performs DQ checks and VACUUM in sequence.

        Args:
            executor: Pipeline executor with batch metrics.

        Returns:
            PostrunResult with DQ and VACUUM results.

        Raises:
            DataQualityThresholdError: If error rate exceeds hard threshold.
        """
        dq_result = await self.run_dq_checks(executor)
        vacuum_result = await self.run_vacuum_if_enabled()
        return PostrunResult(dq=dq_result, vacuum=vacuum_result)

    async def run_dq_checks(self, executor: ExecutorMetricsProtocol) -> DQResult:
        """Check data quality metrics and report anomalies.

        Delegates to DataQualityService for threshold checks and anomaly detection.

        Args:
            executor: Pipeline executor with batch metrics.

        Returns:
            DQResult with evaluation results.

        Raises:
            DataQualityThresholdError: If error rate exceeds hard threshold.
        """
        batch_metrics = self._collect_batch_metrics(executor)
        return await self._dq_service.evaluate(batch_metrics)

    async def run_vacuum_if_enabled(self) -> VacuumResult:
        """Run VACUUM on Silver and Gold tables if enabled.

        Delegates to MedallionLifecycleService.finalize_run() which handles:
        - Checking if vacuum is enabled
        - Skipping in dry-run mode
        - Vacuuming both Silver and Gold tables
        - Metrics emission

        Returns:
            VacuumResult with operation details.
        """
        return await self._lifecycle_service.finalize_run(
            config=self._config,
            runtime=self._runtime,
            metrics=self._metrics,
        )

    async def cleanup(self, tracer: TracingPort | None) -> None:
        """Cleanup all resources including observability.

        Ensures tracer spans are flushed before shutdown (O3).
        Handles errors gracefully to avoid masking pipeline exceptions.

        Args:
            tracer: Optional tracing port to close.
        """
        if tracer is not None:
            try:
                tracer.close()
                self._logger.debug("Tracer closed successfully")
            except Exception as e:
                self._logger.warning(
                    "Failed to close tracer",
                    error=str(e),
                )

    def _collect_batch_metrics(
        self, executor: ExecutorMetricsProtocol
    ) -> dict[str, float]:
        """Collect batch metrics from executor.

        Args:
            executor: Pipeline executor with batch metrics.

        Returns:
            Dictionary of metric names to values.
        """
        total_records = max(1, executor.records_fetched)
        return {
            "record_count": float(executor.records_fetched),
            "bronze_count": float(executor.records_bronze),
            "silver_count": float(executor.records_silver),
            "gold_count": float(executor.records_gold),
            "quarantined_count": float(executor.records_quarantined),
            "error_rate": executor.records_quarantined / total_records,
            "silver_yield": executor.records_silver / total_records,
            "gold_yield": executor.records_gold / total_records,
        }


__all__ = [
    "DQResult",
    "DQStatus",
    "ExecutorMetricsProtocol",
    "PostrunResult",
    "PostrunService",
    "VacuumResult",
]
