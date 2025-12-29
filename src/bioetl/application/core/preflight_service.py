"""Preflight Service for infrastructure validation.

Application Service that validates infrastructure health before pipeline execution.
Extracted from PipelineRunner to follow Single Responsibility Principle.

Decomposed per REFACTOR-003:
- MedallionConfigValidator: handles medallion-specific validation
- HealthAggregator: handles health check aggregation
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from bioetl.application.core.health_aggregator import HealthAggregator
from bioetl.application.core.medallion_validator import MedallionConfigValidator
from bioetl.domain.types import (
    ConfigValidationError,
    HealthReport,
    HealthStatus,
    PreflightReport,
)

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort, MetricsPort


class PreflightService:
    """Validates infrastructure health before pipeline execution.

    Responsibilities:
    - Pre-flight health checks for storage and data source (via HealthAggregator)
    - Medallion configuration validation (via MedallionConfigValidator)
    - Recording preflight metrics
    - Fail-fast on infrastructure issues

    Decomposed per REFACTOR-003:
    - Delegates medallion validation to MedallionConfigValidator
    - Delegates health checks to HealthAggregator

    Attributes:
        _config: Pipeline configuration.
        _context: Pipeline execution context.
        _logger: Structured logger.
        _metrics: Metrics port for recording.
        _health_aggregator: Health check aggregator.
        _medallion_validator: Medallion configuration validator.

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
        self._medallion_validator = MedallionConfigValidator(
            config=config,
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

    def validate_medallion_config(
        self,
        runtime: RuntimeConfig,
        bronze_path: str,
        silver_path: str,
        gold_path: str,
        silver_format: str | None = None,
        gold_format: str | None = None,
    ) -> list[ConfigValidationError]:
        """Validate Medallion architecture invariants before pipeline execution.

        Delegates to MedallionConfigValidator.

        Args:
            runtime: Runtime configuration with run type.
            bronze_path: Base path for Bronze layer storage.
            silver_path: Base path for Silver layer storage.
            gold_path: Base path for Gold layer storage.
            silver_format: Format of Silver layer (e.g., "delta", "parquet").
            gold_format: Format of Gold layer (e.g., "delta", "parquet").

        Returns:
            List of ConfigValidationError objects. Empty list means validation passed.

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
        """Validate that config write modes are allowed by medallion policy.

        Delegates to MedallionConfigValidator.

        Returns:
            List of ConfigValidationError if write modes violate policy.

        """
        return self._medallion_validator.validate_write_modes()

    async def validate_preflight(
        self,
        services: PipelineServices,
        runtime: RuntimeConfig,
        bronze_path: str,
        silver_path: str,
        gold_path: str,
        silver_format: str | None = None,
        gold_format: str | None = None,
    ) -> PreflightReport:
        """Execute complete preflight validation.

        Performs all preflight checks:
        1. Infrastructure health validation
        2. Medallion config validation
        3. Write mode policy validation

        Args:
            services: Pipeline services for health checks.
            runtime: Runtime configuration.
            bronze_path: Base path for Bronze layer storage.
            silver_path: Base path for Silver layer storage.
            gold_path: Base path for Gold layer storage.
            silver_format: Format of Silver layer.
            gold_format: Format of Gold layer.

        Returns:
            PreflightReport with aggregated validation results.

        Raises:
            InfrastructureError: If critical infrastructure is unhealthy
                and strict_validation is enabled.
            ValueError: If medallion policy is invalid and strict_validation
                is enabled.

        """
        self._logger.info(
            "Starting preflight validation",
            extra={"stage": "preflight", "strict_mode": runtime.strict_validation},
        )

        # 1. Validate infrastructure health
        health_report = await self.validate_infrastructure(services)

        # 2. Validate medallion config
        config_errors = self.validate_medallion_config(
            runtime=runtime,
            bronze_path=bronze_path,
            silver_path=silver_path,
            gold_path=gold_path,
            silver_format=silver_format,
            gold_format=gold_format,
        )

        # 3. Validate write modes against policy
        write_mode_errors = self.validate_write_modes()
        config_errors.extend(write_mode_errors)

        # Determine if medallion policy is valid
        medallion_policy_valid = len(config_errors) == 0

        # Create preflight report
        report = PreflightReport(
            health_report=health_report,
            medallion_policy_valid=medallion_policy_valid,
            config_errors=config_errors,
        )

        # Record metrics
        self._record_preflight_metrics(report)

        # Log final result
        self._logger.info(
            "Preflight validation completed",
            extra={
                "stage": "preflight",
                "medallion_policy_valid": medallion_policy_valid,
                "config_error_count": len(config_errors),
                "is_healthy": health_report.is_healthy,
                "should_block": report.should_block_startup,
            },
        )

        # Block startup if validation failed and strict mode is enabled
        if report.should_block_startup and runtime.strict_validation:
            error_messages = [
                f"{e.field}: {e.actual} (expected: {e.expected})" for e in config_errors
            ]
            raise ValueError(
                f"Preflight validation failed (strict mode): {', '.join(error_messages)}"
            )

        return report

    def _record_preflight_metrics(self, report: PreflightReport) -> None:
        """Record preflight validation metrics.

        Records:
        - preflight_medallion_policy_valid: Whether policy validation passed
        - preflight_config_errors_total: Count of configuration errors

        Args:
            report: PreflightReport with validation results.

        """
        pipeline = self._config.pipeline_name
        run_id = str(self._context.run_id)

        # Record medallion policy validation status
        self._metrics.set_gauge(
            "preflight_medallion_policy_valid",
            1.0 if report.medallion_policy_valid else 0.0,
            {"pipeline": pipeline, "run_id": run_id},
        )

        # Record config error count
        self._metrics.set_gauge(
            "preflight_config_errors_total",
            float(len(report.config_errors)),
            {"pipeline": pipeline, "run_id": run_id},
        )


__all__ = ["PreflightService"]
