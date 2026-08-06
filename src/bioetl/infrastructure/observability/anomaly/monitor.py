"""Data quality monitoring using typed domain anomaly DTOs."""

from __future__ import annotations

__all__ = ["DataQualityMonitor"]


from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.value_objects.dq_anomaly import DQAnomaly, DQAnomalySeverity
from bioetl.infrastructure.observability.anomaly.detector import AnomalyDetector

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.domain.ports import LoggerPort


class DataQualityMonitor:
    """Monitor data quality metrics and detect issues.

    Combines multiple detectors to monitor:
    - Record count stability
    - Processing time consistency
    - Error rate thresholds
    - Validation failure rates

    Usage:
        monitor = DataQualityMonitor(logger=my_logger)
        monitor.add_metric("record_count", baseline=[1000, 1050, 980])

        issues = monitor.check_quality({
            "record_count": 500,
            "error_rate": 0.15,
        })
        for issue in issues:
            logger.warning(
                "Data quality issue detected",
                stage="validate",
                anomaly_metric=issue.metric_name,
                severity=issue.severity.value,
            )
    """

    def __init__(
        self,
        logger: LoggerPort,
        baseline_window: int = 7,
        z_score_threshold: float = 2.5,
    ) -> None:
        """Initialize data quality monitor.

        Args:
            logger: Structured logger for observability (MUST be injected)
            baseline_window: Number of days to consider for baseline (default: 7)
            z_score_threshold: Z-score threshold for anomaly detection (default: 2.5)

        """
        self._logger = logger
        self.detector = AnomalyDetector(
            baseline_window=baseline_window,
            z_score_threshold=z_score_threshold,
        )

        # Set default thresholds for common metrics
        self.detector.set_threshold("error_rate", min_value=0.0, max_value=0.1)
        self.detector.set_threshold("quality_score", min_value=0.8, max_value=1.0)

    def add_metric(
        self,
        metric_name: str,
        baseline: Sequence[float],
        min_threshold: float | None = None,
        max_threshold: float | None = None,
    ) -> None:
        """Add metric to monitor.

        Args:
            metric_name: Name of the metric.
            baseline: Baseline.
            min_threshold: Minimum threshold.
            max_threshold: Maximum threshold.
        """
        self.detector.update_baseline(metric_name, baseline)
        if min_threshold is not None or max_threshold is not None:
            self.detector.set_threshold(metric_name, min_threshold, max_threshold)

    def check_quality(
        self, metrics: dict[str, float], timestamp: datetime | None = None
    ) -> list[DQAnomaly]:
        """Check metrics for quality issues.

        Args:
            metrics: Dictionary of metric names to values
            timestamp: Timestamp for anomalies (should be created in application layer)

        Returns:
            List of detected domain anomaly DTOs.
        """
        if timestamp is None:
            return []

        anomalies: list[DQAnomaly] = []

        for metric_name, current_value in metrics.items():
            anomaly = self.detector.detect(metric_name, current_value, timestamp)
            if anomaly:
                anomalies.append(anomaly)

        return anomalies

    def update_baseline_from_metrics(
        self, metrics: dict[str, float], timestamp: datetime | None = None
    ) -> None:
        """Update baseline with current metrics (if no anomalies).

        Args:
            metrics: Mapping of metric name to newly observed value.
            timestamp: Mandatory caller-owned timestamp; baseline is not updated
                when timestamp is missing (defensive for non-typed callers).
        """
        if timestamp is None:
            self._logger.warning(
                "Skipping baseline update due to missing timestamp",
            )
            return
        anomalies = self.check_quality(metrics, timestamp)
        critical_anomalies = [
            a for a in anomalies if a.severity == DQAnomalySeverity.CRITICAL
        ]

        if critical_anomalies:
            self._logger.warning(
                "Skipping baseline update due to critical anomalies",
                critical_anomaly_count=len(critical_anomalies),
            )
            return

        for metric_name, value in metrics.items():
            self.detector.add_baseline_value(metric_name, value)

    def get_baseline_stats(
        self,
        metric_name: str,
    ) -> tuple[float, float, int] | None:
        """Get baseline statistics for a metric.

        Returns:
            Tuple of (mean, stddev, sample_count) or None if no baseline

        Args:
            metric_name: Name of the metric.
        """
        return self.detector.get_baseline_stats(metric_name)
