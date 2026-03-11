"""Preflight service for infrastructure and Medallion validation."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from bioetl.application.core.preflight.health_aggregator import _HealthAggregator
from bioetl.application.core.preflight.medallion_validator import (
    _MedallionConfigValidator,
)
from bioetl.domain.types import (
    ConfigValidationError,
    HealthReport,
    HealthStatus,
    PreflightReport,
)

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort, MetricsPort


class PreflightService:
    """Validates infrastructure and configuration before pipeline execution."""

    def __init__(
        self,
        config: PipelineConfig,
        context: PipelineContext,
        logger: LoggerPort,
        metrics: MetricsPort,
        health_aggregator: _HealthAggregator,
        medallion_validator: _MedallionConfigValidator,
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
        pipeline = self._config.pipeline_name
        run_id = str(self._context.run_id)

        for result in report.results:
            passed = 1.0 if result.status == HealthStatus.HEALTHY else 0.0
            self._metrics.set_gauge(
                "pipeline_health_check_passed",
                passed,
                {"pipeline": pipeline, "component": result.component},
            )

        validated = 1.0 if report.is_healthy else 0.0
        self._metrics.set_gauge(
            "infrastructure_validated",
            validated,
            {"pipeline": pipeline, "run_id": run_id},
        )

        self._metrics.observe_histogram(
            "health_check_duration_seconds",
            duration,
            {"pipeline": pipeline},
        )

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
        pipeline = self._config.pipeline_name
        run_id = str(self._context.run_id)

        self._metrics.set_gauge(
            "preflight_medallion_policy_valid",
            1.0 if report.medallion_policy_valid else 0.0,
            {"pipeline": pipeline, "run_id": run_id},
        )

        self._metrics.set_gauge(
            "preflight_config_errors_total",
            float(len(report.config_errors)),
            {"pipeline": pipeline, "run_id": run_id},
        )

    def _log_preflight_started(self, runtime: RuntimeConfig) -> None:
        """Log preflight start event."""
        self._logger.info(
            "Starting preflight validation",
            extra={"stage": "preflight", "strict_mode": runtime.strict_validation},
        )

    def _log_preflight_completed(
        self, report: PreflightReport, is_healthy: bool
    ) -> None:
        """Log preflight completion event."""
        self._logger.info(
            "Preflight validation completed",
            extra={
                "stage": "preflight",
                "medallion_policy_valid": report.medallion_policy_valid,
                "config_error_count": len(report.config_errors),
                "is_healthy": is_healthy,
                "should_block": report.should_block_startup,
            },
        )

    def _raise_if_strict_blocking(
        self,
        report: PreflightReport,
        runtime: RuntimeConfig,
    ) -> None:
        """Raise strict-mode preflight error when startup should be blocked."""
        if not (report.should_block_startup and runtime.strict_validation):
            return
        error_messages = [
            f"{error.field}: {error.actual} (expected: {error.expected})"
            for error in report.config_errors
        ]
        raise ValueError(
            "Preflight validation failed (strict mode): " + ", ".join(error_messages)
        )


__all__ = ["PreflightService", "_HealthAggregator", "_MedallionConfigValidator"]
