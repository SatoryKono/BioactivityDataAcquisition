"""Preflight Service for infrastructure validation.

Application Service that validates infrastructure health before pipeline execution.
Extracted from PipelineRunner to follow Single Responsibility Principle.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from bioetl.application.core.health_aggregator import HealthAggregator
from bioetl.domain.types import HealthReport, HealthStatus

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.domain.config import PipelineConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort, MetricsPort


class PreflightService:
    """Validates infrastructure health before pipeline execution.

    Responsibilities:
    - Pre-flight health checks for storage and data source
    - Recording health check metrics
    - Fail-fast on infrastructure issues

    Attributes:
        _config: Pipeline configuration.
        _context: Pipeline execution context.
        _logger: Structured logger.
        _health_aggregator: Health check aggregator.
    """

    def __init__(
        self,
        config: PipelineConfig,
        context: PipelineContext,
        logger: LoggerPort,
        metrics: MetricsPort,
    ) -> None:
        """Initialize preflight service.

        Args:
            config: Pipeline configuration.
            context: Pipeline execution context.
            logger: Structured logger.
            metrics: Metrics port for recording health check metrics.
        """
        self._config = config
        self._context = context
        self._logger = logger
        self._metrics = metrics
        self._health_aggregator = HealthAggregator(
            metrics=metrics,
            logger=logger,
        )

    async def validate_infrastructure(self, services: PipelineServices) -> HealthReport:
        """Validate infrastructure health before pipeline execution.

        Performs health checks on storage and data source components.
        Records metrics per Unified Observability Contract:
        - pipeline_health_check_passed: Per-component health status (1=passed, 0=failed)
        - infrastructure_validated: Overall validation status
        - health_check_duration_seconds: Total health check duration

        Args:
            services: Pipeline services containing storage and data source.

        Returns:
            HealthReport with aggregated results.

        Raises:
            InfrastructureError: If critical components are unhealthy.
        """
        self._logger.info(
            "Validating infrastructure health",
            extra={"stage": "health_check"},
        )

        start_time = time.perf_counter()
        report = await self._health_aggregator.check_all(services)
        duration = time.perf_counter() - start_time

        self._record_health_check_metrics(report, duration)

        self._logger.info(
            "Infrastructure health check completed",
            extra={
                "stage": "health_check",
                "overall_status": report.overall_status.value,
                "is_healthy": report.is_healthy,
                "components_checked": len(report.results),
                "duration_seconds": round(duration, 4),
            },
        )

        # Fail-fast if any critical component is unhealthy
        self._health_aggregator.assert_healthy(report)

        return report

    def _record_health_check_metrics(
        self,
        report: Any,
        duration: float,
    ) -> None:
        """Record health-check metrics per Unified Observability Contract.

        Records:
        - pipeline_health_check_passed: Per-component status (1=passed, 0=failed)
        - infrastructure_validated: Overall validation status
        - health_check_duration_seconds: Total duration

        Args:
            report: HealthReport from health aggregator.
            duration: Total health check duration in seconds.
        """
        pipeline = self._config.pipeline_name
        run_id = str(self._context.run_id)

        # Record per-component health check passed status
        for result in report.results:
            passed = 1.0 if result.status == HealthStatus.HEALTHY else 0.0
            self._metrics.set_gauge(
                "pipeline_health_check_passed",
                passed,
                {"pipeline": pipeline, "component": result.component},
            )

        # Record overall infrastructure validation status
        validated = 1.0 if report.is_healthy else 0.0
        self._metrics.set_gauge(
            "infrastructure_validated",
            validated,
            {"pipeline": pipeline, "run_id": run_id},
        )

        # Record health check duration
        self._metrics.observe_histogram(
            "health_check_duration_seconds",
            duration,
            {"pipeline": pipeline},
        )


__all__ = ["PreflightService"]
