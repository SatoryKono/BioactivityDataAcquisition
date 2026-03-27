"""Preflight service for infrastructure and Medallion validation."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from bioetl.application.core.preflight.health_aggregator import HealthAggregator
from bioetl.application.core.preflight.medallion_validator import (
    MedallionConfigValidator,
)
from bioetl.application.core.preflight.preflight_reporting import (
    log_preflight_completed,
    log_preflight_started,
    raise_if_strict_blocking,
    record_health_check_metrics,
    record_preflight_metrics,
)
from bioetl.domain.types import (
    ConfigValidationError,
    HealthReport,
    PreflightReport,
)

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort, MetricsPort


# Backward-compatible aliases retained for legacy tests/import paths that still
# resolve the helper classes via preflight.service.
_HealthAggregator = HealthAggregator
_MedallionConfigValidator = MedallionConfigValidator


class PreflightService:
    """Validates infrastructure and configuration before pipeline execution."""

    def __init__(
        self,
        config: PipelineConfig,
        context: PipelineContext,
        logger: LoggerPort,
        metrics: MetricsPort,
        health_aggregator: HealthAggregator,
        medallion_validator: MedallionConfigValidator,
    ) -> None:
        self._config = config
        self._context = context
        self._logger = logger
        self._metrics = metrics
        self._health_aggregator = health_aggregator
        self._medallion_validator = medallion_validator

    async def validate_infrastructure(self, services: PipelineService) -> HealthReport:
        """Validate storage and data source health.

        Args:
            services: Pipeline service container providing storage and data source ports.

        Returns:
            HealthReport with per-component status and overall health assessment.
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

        self._health_aggregator.assert_healthy(report)
        return report

    def _record_health_check_metrics(
        self, report: HealthReport, duration: float
    ) -> None:
        """Record health-check metrics per observability contract."""
        record_health_check_metrics(self, report, duration)

    def validate_medallion_config(
        self,
        runtime: RuntimeConfig,
        bronze_path: str,
        silver_path: str,
        gold_path: str,
        silver_format: str | None = None,
        gold_format: str | None = None,
    ) -> list[ConfigValidationError]:
        """Validate Medallion architecture invariants.

        Args:
            runtime: Runtime configuration specifying run type and write modes.
            bronze_path: Absolute path to the Bronze layer directory.
            silver_path: Absolute path to the Silver layer directory.
            gold_path: Absolute path to the Gold layer directory.
            silver_format: Optional storage format override for Silver (e.g. ``"delta"``).
            gold_format: Optional storage format override for Gold.

        Returns:
            List of ConfigValidationError for any detected violations (empty if valid).
        """
        return self._medallion_validator.validate_medallion_config(
            runtime=runtime,
            bronze_path=bronze_path,
            silver_path=silver_path,
            gold_path=gold_path,
            silver_format=silver_format,
            gold_format=gold_format,
        )

    def validate_write_modes(self) -> list[ConfigValidationError]:
        """Validate that config write modes are allowed by Medallion policy.

        Returns:
            List of ConfigValidationError for any invalid write mode combinations.
        """
        return self._medallion_validator.validate_write_modes()

    async def validate_preflight(
        self,
        services: PipelineService,
        runtime: RuntimeConfig,
        bronze_path: str,
        silver_path: str,
        gold_path: str,
        silver_format: str | None = None,
        gold_format: str | None = None,
    ) -> PreflightReport:
        """Execute all preflight checks and return aggregated report.

        Args:
            services: Pipeline service container for infrastructure health checks.
            runtime: Runtime configuration used for Medallion invariant validation.
            bronze_path: Absolute path to the Bronze layer directory.
            silver_path: Absolute path to the Silver layer directory.
            gold_path: Absolute path to the Gold layer directory.
            silver_format: Optional storage format override for Silver.
            gold_format: Optional storage format override for Gold.

        Returns:
            PreflightReport aggregating infrastructure health and config validation results.
        """
        self._log_preflight_started(runtime)

        health_report = await self.validate_infrastructure(services)

        config_errors = self.validate_medallion_config(
            runtime=runtime,
            bronze_path=bronze_path,
            silver_path=silver_path,
            gold_path=gold_path,
            silver_format=silver_format,
            gold_format=gold_format,
        )

        write_mode_errors = self.validate_write_modes()
        config_errors.extend(write_mode_errors)

        medallion_policy_valid = len(config_errors) == 0

        report = PreflightReport(
            health_report=health_report,
            medallion_policy_valid=medallion_policy_valid,
            config_errors=config_errors,
        )

        self._record_preflight_metrics(report)
        self._log_preflight_completed(report, health_report.is_healthy)
        self._raise_if_strict_blocking(report, runtime)

        return report

    def _record_preflight_metrics(self, report: PreflightReport) -> None:
        """Record preflight validation metrics."""
        record_preflight_metrics(self, report)

    def _log_preflight_started(self, runtime: RuntimeConfig) -> None:
        """Log preflight start event."""
        log_preflight_started(self, strict_validation=runtime.strict_validation)

    def _log_preflight_completed(
        self, report: PreflightReport, is_healthy: bool
    ) -> None:
        """Log preflight completion event."""
        log_preflight_completed(self, report, is_healthy=is_healthy)

    def _raise_if_strict_blocking(
        self,
        report: PreflightReport,
        runtime: RuntimeConfig,
    ) -> None:
        """Raise strict-mode preflight error when startup should be blocked."""
        raise_if_strict_blocking(report, strict_validation=runtime.strict_validation)


__all__ = [
    "HealthAggregator",
    "MedallionConfigValidator",
    "PreflightService",
    "_HealthAggregator",
    "_MedallionConfigValidator",
]
