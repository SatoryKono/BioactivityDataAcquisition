"""Anomaly detection for data quality monitoring.

Implements baseline comparison and threshold-based detection for:
- Record count anomalies (sudden drops/spikes)
- Processing time anomalies
- Error rate anomalies
- Data quality score degradation

Uses statistical methods (Z-score, IQR) and configurable thresholds.

Usage:
    detector = AnomalyDetector(baseline_window=7)

    # Update baseline with historical data
    detector.update_baseline("record_count", [1000, 1050, 980, 1020, 1100])

    # Check for anomalies
    anomaly = detector.detect("record_count", 500)
    if anomaly:
        logger.warning(f"Anomaly detected: {anomaly}")
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


class AnomalyType(str, Enum):
    """Types of anomalies that can be detected."""

    SPIKE = "spike"  # Value much higher than baseline
    DROP = "drop"  # Value much lower than baseline
    THRESHOLD_EXCEEDED = "threshold_exceeded"  # Value exceeds configured threshold
    TREND_CHANGE = "trend_change"  # Significant trend deviation


class AnomalySeverity(str, Enum):
    """Severity levels for anomalies."""

    LOW = "low"  # Within 2-3 std deviations
    MEDIUM = "medium"  # Within 3-4 std deviations
    HIGH = "high"  # Beyond 4 std deviations
    CRITICAL = "critical"  # Beyond 5 std deviations or threshold breach


@dataclass(frozen=True)
class Anomaly:
    """Detected anomaly with context.

    Attributes:
        metric_name: Name of metric (e.g., "record_count")
        current_value: Current observed value
        baseline_mean: Historical average
        baseline_stddev: Historical standard deviation
        anomaly_type: Type of anomaly detected
        severity: Severity level
        z_score: Number of standard deviations from mean
        timestamp: When anomaly was detected
        message: Human-readable description
    """

    metric_name: str
    current_value: float
    baseline_mean: float
    baseline_stddev: float
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    z_score: float
    timestamp: datetime
    message: str

    def __str__(self) -> str:
        """Format anomaly as string."""
        return (
            f"[{self.severity.value.upper()}] {self.anomaly_type.value} in {self.metric_name}: "
            f"current={self.current_value:.2f}, baseline={self.baseline_mean:.2f}±{self.baseline_stddev:.2f} "
            f"(z-score={self.z_score:.2f})"
        )


class AnomalyDetector:
    """Statistical anomaly detection for metrics.

    Uses Z-score method with configurable thresholds:
    - Z-score > 2: Low severity
    - Z-score > 3: Medium severity
    - Z-score > 4: High severity
    - Z-score > 5: Critical severity

    Attributes:
        baseline_window: Number of historical data points for baseline (default: 7)
        z_score_threshold: Minimum Z-score to consider anomalous (default: 2.0)
        min_baseline_samples: Minimum samples required for detection (default: 3)
    """

    def __init__(
        self,
        baseline_window: int = 7,
        z_score_threshold: float = 2.0,
        min_baseline_samples: int = 3,
    ) -> None:
        """Initialize anomaly detector.

        Args:
            baseline_window: Number of historical values to keep
            z_score_threshold: Minimum Z-score for anomaly (typically 2-3)
            min_baseline_samples: Minimum samples needed for detection
        """
        if baseline_window < 1:
            raise ValueError("baseline_window must be >= 1")
        if z_score_threshold < 0:
            raise ValueError("z_score_threshold must be >= 0")
        if min_baseline_samples < 1:
            raise ValueError("min_baseline_samples must be >= 1")

        self.baseline_window = baseline_window
        self.z_score_threshold = z_score_threshold
        self.min_baseline_samples = min_baseline_samples

        # Store baseline data per metric
        self._baselines: dict[str, list[float]] = {}

        # Store configured thresholds per metric
        self._thresholds: dict[str, tuple[float, float]] = {}  # (min, max)

    def update_baseline(
        self,
        metric_name: str,
        values: Sequence[float],
    ) -> None:
        """Update baseline with historical data.

        Args:
            metric_name: Name of metric
            values: Historical values (most recent last)
        """
        if not values:
            return

        # Initialize or update baseline
        if metric_name not in self._baselines:
            self._baselines[metric_name] = []

        baseline = self._baselines[metric_name]
        baseline.extend(values)

        # Keep only last N values (window)
        if len(baseline) > self.baseline_window:
            self._baselines[metric_name] = baseline[-self.baseline_window:]

    def add_baseline_value(
        self,
        metric_name: str,
        value: float,
    ) -> None:
        """Add single value to baseline.

        Args:
            metric_name: Name of metric
            value: New baseline value
        """
        self.update_baseline(metric_name, [value])

    def set_threshold(
        self,
        metric_name: str,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> None:
        """Set absolute thresholds for a metric.

        Args:
            metric_name: Name of metric
            min_value: Minimum acceptable value (None = no minimum)
            max_value: Maximum acceptable value (None = no maximum)
        """
        min_val = min_value if min_value is not None else float("-inf")
        max_val = max_value if max_value is not None else float("inf")

        if min_val > max_val:
            raise ValueError("min_value must be <= max_value")

        self._thresholds[metric_name] = (min_val, max_val)

    def _check_thresholds(self, metric_name: str, current_value: float) -> Anomaly | None:
        """Check if the current value exceeds the configured thresholds."""
        if metric_name in self._thresholds:
            min_val, max_val = self._thresholds[metric_name]
            if not (min_val <= current_value <= max_val):
                return self._create_threshold_anomaly(metric_name, current_value, min_val, max_val)
        return None

    def _get_z_score(self, metric_name: str, current_value: float) -> tuple[float, float, float] | None:
        """Calculate the Z-score for the current value."""
        baseline = self._baselines.get(metric_name, [])
        if len(baseline) < self.min_baseline_samples:
            return None

        mean = statistics.mean(baseline)
        stddev = statistics.stdev(baseline) if len(baseline) >= 2 else 0.0

        if stddev == 0:
            if mean == 0:
                return None
            deviation_pct = abs(current_value - mean) / abs(mean)
            return (deviation_pct * 2, mean, stddev) if deviation_pct >= 0.5 else None

        z_score = abs(current_value - mean) / stddev
        return (z_score, mean, stddev)

    def detect(self, metric_name: str, current_value: float) -> Anomaly | None:
        """Detect anomaly in current value."""
        if anomaly := self._check_thresholds(metric_name, current_value):
            return anomaly

        z_score_data = self._get_z_score(metric_name, current_value)
        if not z_score_data:
            return None

        z_score, mean, stddev = z_score_data
        if z_score < self.z_score_threshold:
            return None

        anomaly_type = AnomalyType.SPIKE if current_value > mean else AnomalyType.DROP
        severity = self._get_severity(z_score)
        message = (
            f"{anomaly_type.value.capitalize()} detected: value {current_value:.2f} is "
            f"{z_score:.2f} std deviations from baseline mean {mean:.2f}"
        )

        return Anomaly(
            metric_name=metric_name,
            current_value=current_value,
            baseline_mean=mean,
            baseline_stddev=stddev,
            anomaly_type=anomaly_type,
            severity=severity,
            z_score=z_score,
            timestamp=datetime.now(UTC),
            message=message,
        )

    def _get_severity(self, z_score: float) -> AnomalySeverity:
        """Determine the severity of an anomaly based on its Z-score."""
        if z_score >= 5.0:
            return AnomalySeverity.CRITICAL
        if z_score >= 4.0:
            return AnomalySeverity.HIGH
        if z_score >= 3.0:
            return AnomalySeverity.MEDIUM
        return AnomalySeverity.LOW

    def _create_threshold_anomaly(
        self,
        metric_name: str,
        current_value: float,
        min_val: float,
        max_val: float,
    ) -> Anomaly:
        """Create anomaly for threshold breach.

        Args:
            metric_name: Name of metric
            current_value: Current value
            min_val: Minimum threshold
            max_val: Maximum threshold

        Returns:
            Anomaly object
        """
        # Calculate baseline from thresholds
        baseline_mean = (min_val + max_val) / 2
        baseline_stddev = (max_val - min_val) / 4  # Assume ~95% in range

        # Calculate pseudo z-score
        z_score = abs(current_value - baseline_mean) / baseline_stddev if baseline_stddev > 0 else 10.0

        if current_value < min_val:
            message = f"Value {current_value:.2f} below minimum threshold {min_val:.2f}"
        else:
            message = (
                f"Value {current_value:.2f} exceeds maximum threshold {max_val:.2f}"
            )

        return Anomaly(
            metric_name=metric_name,
            current_value=current_value,
            baseline_mean=baseline_mean,
            baseline_stddev=baseline_stddev,
            anomaly_type=AnomalyType.THRESHOLD_EXCEEDED,
            severity=AnomalySeverity.CRITICAL,
            z_score=z_score,
            timestamp=datetime.now(UTC),
            message=message,
        )

    def clear_baseline(self, metric_name: str) -> None:
        """Clear baseline for a metric.

        Args:
            metric_name: Name of metric to clear
        """
        self._baselines.pop(metric_name, None)

    def get_baseline_stats(
        self,
        metric_name: str,
    ) -> tuple[float, float, int] | None:
        """Get baseline statistics for a metric.

        Args:
            metric_name: Name of metric

        Returns:
            Tuple of (mean, stddev, count) or None if no baseline
        """
        baseline = self._baselines.get(metric_name)
        if not baseline:
            return None

        mean = statistics.mean(baseline)
        stddev = statistics.stdev(baseline) if len(baseline) >= 2 else 0.0

        return (mean, stddev, len(baseline))


class DataQualityMonitor:
    """Monitor data quality metrics and detect issues.

    Combines multiple detectors to monitor:
    - Record count stability
    - Processing time consistency
    - Error rate thresholds
    - Validation failure rates

    Usage:
        monitor = DataQualityMonitor()
        monitor.add_metric("record_count", baseline=[1000, 1050, 980])

        issues = monitor.check_quality({
            "record_count": 500,
            "error_rate": 0.15,
        })
        for issue in issues:
            logger.warning(issue)
    """

    def __init__(
        self,
        baseline_window: int = 7,
        z_score_threshold: float = 2.5,
    ) -> None:
        """Initialize data quality monitor.

        Args:
            baseline_window: Days of historical data for baseline
            z_score_threshold: Z-score threshold for anomalies
        """
        self.detector = AnomalyDetector(
            baseline_window=baseline_window,
            z_score_threshold=z_score_threshold,
        )

        # Set default thresholds for common metrics
        self.detector.set_threshold(
            "error_rate", min_value=0.0, max_value=0.1
        )  # 10% max
        self.detector.set_threshold(
            "quality_score", min_value=0.8, max_value=1.0
        )  # 80% min

    def add_metric(
        self,
        metric_name: str,
        baseline: Sequence[float],
        min_threshold: float | None = None,
        max_threshold: float | None = None,
    ) -> None:
        """Add metric to monitor.

        Args:
            metric_name: Name of metric
            baseline: Historical baseline values
            min_threshold: Optional minimum threshold
            max_threshold: Optional maximum threshold
        """
        self.detector.update_baseline(metric_name, baseline)
        if min_threshold is not None or max_threshold is not None:
            self.detector.set_threshold(metric_name, min_threshold, max_threshold)

    def check_quality(
        self,
        metrics: dict[str, float],
    ) -> list[Anomaly]:
        """Check metrics for quality issues.

        Args:
            metrics: Dictionary of metric_name -> current_value

        Returns:
            List of detected anomalies
        """
        anomalies: list[Anomaly] = []

        for metric_name, current_value in metrics.items():
            anomaly = self.detector.detect(metric_name, current_value)
            if anomaly:
                anomalies.append(anomaly)

        return anomalies

    def update_baseline_from_metrics(
        self,
        metrics: dict[str, float],
    ) -> None:
        """Update baseline with current metrics (if no anomalies).

        Args:
            metrics: Dictionary of metric_name -> current_value
        """
        # Only update baseline if no critical anomalies
        anomalies = self.check_quality(metrics)
        critical_anomalies = [
            a for a in anomalies if a.severity == AnomalySeverity.CRITICAL
        ]

        if critical_anomalies:
            logger.warning(
                f"Skipping baseline update due to {len(critical_anomalies)} critical anomalies"
            )
            return

        # Update baseline for all metrics
        for metric_name, value in metrics.items():
            self.detector.add_baseline_value(metric_name, value)
