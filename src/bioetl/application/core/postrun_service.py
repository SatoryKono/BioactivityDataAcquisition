"""Postrun Service for post-execution operations.

Application Service that handles DQ checks, VACUUM, and cleanup after pipeline execution.
Extracted from PipelineRunner to follow Single Responsibility Principle.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from bioetl.domain.exceptions.data_quality import DataQualityThresholdError

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.ports import LoggerPort, TracingPort


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
class DQResult:
    """Result of data quality check.

    Attributes:
        anomalies_count: Number of anomalies detected.
        has_critical: Whether any critical anomalies were found.
        check_duration_ms: Duration of the check in milliseconds.
    """

    anomalies_count: int
    has_critical: bool
    check_duration_ms: float


@dataclass(frozen=True, slots=True)
class VacuumResult:
    """Result of VACUUM operation.

    Attributes:
        silver_files_removed: Number of files removed from Silver table.
        gold_files_removed: Number of files removed from Gold table.
        skipped: Whether VACUUM was skipped.
    """

    silver_files_removed: int
    gold_files_removed: int
    skipped: bool


class PostrunService:
    """Handles post-execution operations.

    Responsibilities:
    - Data quality checks and anomaly detection
    - VACUUM operations on Delta tables
    - Tracer cleanup

    Attributes:
        _config: Pipeline configuration.
        _runtime: Runtime configuration.
        _services: Pipeline services.
        _logger: Structured logger.
        _lifecycle_service: Medallion lifecycle service for VACUUM.
    """

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineServices,
        logger: LoggerPort,
        lifecycle_service: MedallionLifecycleService,
    ) -> None:
        """Initialize postrun service.

        Args:
            config: Pipeline configuration.
            runtime: Runtime configuration.
            services: Pipeline services.
            logger: Structured logger.
            lifecycle_service: Medallion lifecycle service for VACUUM.
        """
        self._config = config
        self._runtime = runtime
        self._services = services
        self._logger = logger
        self._lifecycle_service = lifecycle_service

    async def run_dq_checks(self, executor: ExecutorMetricsProtocol) -> DQResult:
        """Check data quality metrics and report anomalies.

        Performs threshold checks before anomaly detection:
        1. If error_rate >= hard_fail_threshold: raises DataQualityThresholdError
        2. If error_rate >= soft_fail_threshold: logs warning + emits metric
        3. Then runs anomaly detection if dq_monitor is available

        Args:
            executor: Pipeline executor with batch metrics.

        Returns:
            DQResult with anomaly detection results.

        Raises:
            DataQualityThresholdError: If error rate exceeds hard threshold.
        """
        batch_metrics = self._collect_batch_metrics(executor)
        error_rate = batch_metrics["error_rate"]

        self._check_hard_threshold(error_rate)
        self._check_soft_threshold(error_rate)

        if self._services.dq_monitor is None:
            return DQResult(anomalies_count=0, has_critical=False, check_duration_ms=0)

        return self._run_anomaly_detection(batch_metrics)

    def _check_hard_threshold(self, error_rate: float) -> None:
        """Check if error rate exceeds hard threshold.

        Args:
            error_rate: Current error rate.

        Raises:
            DataQualityThresholdError: If threshold exceeded.
        """
        if error_rate >= self._config.dq.hard_fail_threshold:
            self._logger.error(
                "DQ hard threshold exceeded",
                error_rate=error_rate,
                threshold=self._config.dq.hard_fail_threshold,
                pipeline=self._config.pipeline_name,
            )
            raise DataQualityThresholdError(
                error_rate=error_rate,
                threshold=self._config.dq.hard_fail_threshold,
            )

    def _check_soft_threshold(self, error_rate: float) -> None:
        """Check if error rate exceeds soft threshold and log warning.

        Args:
            error_rate: Current error rate.
        """
        if error_rate < self._config.dq.soft_fail_threshold:
            return

        self._logger.warning(
            "DQ soft threshold exceeded",
            error_rate=error_rate,
            threshold=self._config.dq.soft_fail_threshold,
            pipeline=self._config.pipeline_name,
        )
        if self._services.metrics:
            self._services.metrics.increment_counter(
                "dq_soft_threshold_exceeded",
                1,
                {"pipeline": self._config.pipeline_name},
            )

    def _run_anomaly_detection(self, batch_metrics: dict[str, float]) -> DQResult:
        """Run anomaly detection and process results.

        Args:
            batch_metrics: Metrics to check for anomalies.

        Returns:
            DQResult with anomaly detection results.

        Note:
            Caller must ensure dq_monitor is not None before calling.
        """
        # Caller ensures dq_monitor is not None (checked in run_dq_checks)
        assert self._services.dq_monitor is not None
        start_time = time.monotonic()
        anomalies = self._services.dq_monitor.check_quality(batch_metrics)
        check_duration_ms = (time.monotonic() - start_time) * 1000

        self._record_check_duration(check_duration_ms)

        has_critical = self._process_anomalies(anomalies)

        self._services.dq_monitor.update_baseline_from_metrics(batch_metrics)
        self._update_baseline_metrics(batch_metrics, has_critical)

        return DQResult(
            anomalies_count=len(anomalies),
            has_critical=has_critical,
            check_duration_ms=check_duration_ms,
        )

    def _record_check_duration(self, duration_ms: float) -> None:
        """Record DQ check duration metric.

        Args:
            duration_ms: Duration in milliseconds.
        """
        if self._services.metrics:
            self._services.metrics.observe_histogram(
                "dq_check_duration_ms",
                duration_ms,
                {"pipeline": self._config.pipeline_name},
            )

    def _process_anomalies(self, anomalies: list[Any]) -> bool:
        """Process detected anomalies and check for critical ones.

        Args:
            anomalies: List of detected anomalies.

        Returns:
            True if any critical anomalies found.
        """
        has_critical = False
        for anomaly in anomalies:
            self._process_anomaly(anomaly)
            if anomaly.severity.value == "critical":
                has_critical = True
        return has_critical

    def _update_baseline_metrics(
        self, batch_metrics: dict[str, float], has_critical: bool
    ) -> None:
        """Update baseline metrics counters.

        Args:
            batch_metrics: Metrics used for baseline.
            has_critical: Whether critical anomalies were found.
        """
        if not self._services.metrics or has_critical:
            return

        for metric_name in batch_metrics:
            self._services.metrics.increment_counter(
                "dq_baseline_updated",
                1,
                {"pipeline": self._config.pipeline_name, "metric": metric_name},
            )

    async def run_vacuum_if_enabled(self) -> VacuumResult:
        """Run VACUUM on Silver and Gold tables if enabled.

        Executes VACUUM using MedallionLifecycleService when:
        - runtime.vacuum_after_run is True
        - runtime.dry_run is False (no vacuum in dry-run mode)

        Returns:
            VacuumResult with operation details.
        """
        if not self._runtime.vacuum_after_run:
            return VacuumResult(
                silver_files_removed=0, gold_files_removed=0, skipped=True
            )

        if self._runtime.dry_run:
            self._logger.info(
                "VACUUM skipped in dry-run mode",
                extra={"stage": "vacuum"},
            )
            return VacuumResult(
                silver_files_removed=0, gold_files_removed=0, skipped=True
            )

        self._logger.info(
            "Starting VACUUM operation",
            extra={
                "stage": "vacuum",
                "retention_days": self._runtime.vacuum_retention_days,
            },
        )

        gold_table = (
            self._config.gold_table
            or f"{self._config.provider}.{self._config.entity_type}"
        )

        silver_files = await self._vacuum_table(self._config.silver_table, "silver")
        gold_files = await self._vacuum_table(gold_table, "gold")

        return VacuumResult(
            silver_files_removed=silver_files,
            gold_files_removed=gold_files,
            skipped=False,
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

    def _collect_batch_metrics(self, executor: ExecutorMetricsProtocol) -> dict[str, float]:
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

    def _process_anomaly(self, anomaly: Any) -> None:
        """Log and track a single anomaly.

        Args:
            anomaly: Detected anomaly to process.
        """
        self._logger.warning(
            "dq_anomaly_detected",
            anomaly_type=anomaly.anomaly_type.value,
            severity=anomaly.severity.value,
            metric=anomaly.metric_name,
            current_value=anomaly.current_value,
            baseline_mean=anomaly.baseline_mean,
            baseline_stddev=anomaly.baseline_stddev,
            z_score=anomaly.z_score,
            message=anomaly.message,
        )

        if self._services.metrics:
            self._services.metrics.increment_counter(
                "dq_anomaly_detected",
                1,
                {
                    "pipeline": self._config.pipeline_name,
                    "metric": anomaly.metric_name,
                    "severity": anomaly.severity.value,
                    "anomaly_type": anomaly.anomaly_type.value,
                },
            )

        if anomaly.severity.value == "critical":
            self._logger.error(
                "critical_dq_anomaly",
                metric=anomaly.metric_name,
                message=anomaly.message,
            )

    async def _vacuum_table(self, table: str, layer: str) -> int:
        """Vacuum a single table with error handling.

        Args:
            table: Table name to vacuum.
            layer: Layer name for metrics (silver/gold).

        Returns:
            Number of files removed.
        """
        try:
            files_removed = await self._lifecycle_service.vacuum(
                table=table,
                retention_days=self._runtime.vacuum_retention_days,
                dry_run=False,
            )
            self._logger.info(
                f"VACUUM completed for {layer.capitalize()} table",
                extra={
                    "table": table,
                    "files_removed": files_removed,
                },
            )

            if self._services.metrics:
                self._services.metrics.increment_counter(
                    "vacuum_files_removed",
                    files_removed,
                    {"pipeline": self._config.pipeline_name, "layer": layer},
                )
            return files_removed
        except Exception as e:
            self._logger.warning(
                f"VACUUM failed for {layer.capitalize()} table",
                extra={"table": table, "error": str(e)},
            )
            return 0


__all__ = ["DQResult", "PostrunService", "VacuumResult"]
