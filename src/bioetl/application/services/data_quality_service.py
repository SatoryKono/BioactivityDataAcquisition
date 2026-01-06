"""Data Quality Service for centralized DQ evaluation.

Application Service that handles all data quality checks and anomaly detection.
Extracted from PostrunService to follow Single Responsibility Principle.

Responsibilities:
- Threshold checks (soft/hard fail)
- Anomaly detection via DQMonitorPort
- DQ metrics emission
- Baseline updates

Does NOT handle:
- VACUUM operations (MedallionLifecycleService)
- Tracer cleanup (PostrunService)
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from bioetl.domain.exceptions.data_quality import DataQualityThresholdError
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult

if TYPE_CHECKING:
    from bioetl.domain.config import DQConfig
    from bioetl.domain.ports import DQMonitorPort, LoggerPort, MetricsPort


class DataQualityService:
    """Centralized service for data quality evaluation.

    Performs threshold checks, anomaly detection, and metrics emission.
    Designed to be injected into PostrunService or used standalone.

    Attributes:
        _dq_monitor: Optional DQ monitor for anomaly detection.
        _config: DQ configuration with thresholds.
        _logger: Structured logger for DQ events.
        _metrics: Optional metrics port for observability.
        _pipeline_name: Pipeline name for metric labels.
    """

    def __init__(
        self,
        dq_monitor: DQMonitorPort | None,
        config: DQConfig,
        logger: LoggerPort,
        metrics: MetricsPort | None,
        pipeline_name: str,
    ) -> None:
        """Initialize DataQualityService.

        Args:
            dq_monitor: Optional DQ monitor for anomaly detection.
            config: DQ configuration with soft/hard thresholds.
            logger: Structured logger for DQ events.
            metrics: Optional metrics port for observability.
            pipeline_name: Pipeline name for metric labels.
        """
        self._dq_monitor = dq_monitor
        self._config = config
        self._logger = logger
        self._metrics = metrics
        self._pipeline_name = pipeline_name

    async def evaluate(
        self,
        metrics: dict[str, float],
    ) -> DQResult:
        """Evaluate data quality based on metrics.

        Performs threshold checks before anomaly detection:
        1. If error_rate >= hard_fail_threshold: raises DataQualityThresholdError
        2. If error_rate >= soft_fail_threshold: logs warning + emits metric
        3. Then runs anomaly detection if dq_monitor is available

        Args:
            metrics: Dictionary of metric names to values.
                     Must contain 'error_rate' key.

        Returns:
            DQResult with evaluation outcome.

        Raises:
            DataQualityThresholdError: If error rate exceeds hard threshold.
        """
        error_rate = metrics.get("error_rate", 0.0)

        # Check hard threshold first - raises if exceeded
        self._check_hard_threshold(error_rate)

        # Determine status based on soft threshold
        status = self._determine_status(error_rate)

        # Log warning and emit metric if soft threshold exceeded
        if status == DQEvaluationStatus.WARNING:
            self._emit_soft_threshold_warning(error_rate)

        # Run anomaly detection if monitor available
        if self._dq_monitor is None:
            return DQResult(
                error_rate=error_rate,
                status=status,
                anomalies=(),
                has_critical=False,
                check_duration_ms=0.0,
            )

        return self._run_anomaly_detection(metrics, error_rate, status)

    def _check_hard_threshold(self, error_rate: float) -> None:
        """Check if error rate exceeds hard threshold.

        Args:
            error_rate: Current error rate.

        Raises:
            DataQualityThresholdError: If threshold exceeded.
        """
        if error_rate >= self._config.hard_fail_threshold:
            self._logger.error(
                "DQ hard threshold exceeded",
                error_rate=error_rate,
                threshold=self._config.hard_fail_threshold,
                pipeline=self._pipeline_name,
            )
            raise DataQualityThresholdError(
                error_rate=error_rate,
                threshold=self._config.hard_fail_threshold,
            )

    def _determine_status(self, error_rate: float) -> DQEvaluationStatus:
        """Determine DQ status based on error rate.

        Args:
            error_rate: Current error rate.

        Returns:
            DQEvaluationStatus based on threshold comparison.
        """
        if error_rate >= self._config.soft_fail_threshold:
            return DQEvaluationStatus.WARNING
        return DQEvaluationStatus.PASSED

    def _emit_soft_threshold_warning(self, error_rate: float) -> None:
        """Log warning and emit metric for soft threshold breach.

        Args:
            error_rate: Current error rate.
        """
        self._logger.warning(
            "DQ soft threshold exceeded",
            error_rate=error_rate,
            threshold=self._config.soft_fail_threshold,
            pipeline=self._pipeline_name,
        )
        if self._metrics:
            self._metrics.increment_counter(
                "dq_soft_threshold_exceeded",
                1,
                {"pipeline": self._pipeline_name},
            )

    def _run_anomaly_detection(
        self,
        metrics: dict[str, float],
        error_rate: float,
        status: DQEvaluationStatus,
    ) -> DQResult:
        """Run anomaly detection and process results.

        Args:
            metrics: Metrics to check for anomalies.
            error_rate: Calculated error rate.
            status: Determined DQ status.

        Returns:
            DQResult with anomaly detection results.

        Note:
            Caller must ensure dq_monitor is not None before calling.
        """
        assert self._dq_monitor is not None

        start_time = time.monotonic()
        anomalies = self._dq_monitor.check_quality(metrics)
        check_duration_ms = (time.monotonic() - start_time) * 1000

        self._record_check_duration(check_duration_ms)

        has_critical = self._process_anomalies(anomalies)

        # Update baseline only if no critical anomalies
        self._dq_monitor.update_baseline_from_metrics(metrics)
        self._update_baseline_metrics(metrics, has_critical)

        return DQResult(
            error_rate=error_rate,
            status=status,
            anomalies=tuple(anomalies),
            has_critical=has_critical,
            check_duration_ms=check_duration_ms,
        )

    def _record_check_duration(self, duration_ms: float) -> None:
        """Record DQ check duration metric.

        Args:
            duration_ms: Duration in milliseconds.
        """
        if self._metrics:
            self._metrics.observe_histogram(
                "dq_check_duration_ms",
                duration_ms,
                {"pipeline": self._pipeline_name},
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
            self._process_single_anomaly(anomaly)
            if anomaly.severity.value == "critical":
                has_critical = True
        return has_critical

    def _process_single_anomaly(self, anomaly: Any) -> None:
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

        if self._metrics:
            self._metrics.increment_counter(
                "dq_anomaly_detected",
                1,
                {
                    "pipeline": self._pipeline_name,
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

    def _update_baseline_metrics(
        self, metrics: dict[str, float], has_critical: bool
    ) -> None:
        """Update baseline metrics counters.

        Args:
            metrics: Metrics used for baseline.
            has_critical: Whether critical anomalies were found.
        """
        if not self._metrics or has_critical:
            return

        for metric_name in metrics:
            self._metrics.increment_counter(
                "dq_baseline_updated",
                1,
                {"pipeline": self._pipeline_name, "metric": metric_name},
            )


__all__ = ["DataQualityService"]
