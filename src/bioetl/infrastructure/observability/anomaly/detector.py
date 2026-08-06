"""Typed anomaly detector with configurable strategy.

Main entry point for anomaly detection functionality.
"""

from __future__ import annotations

__all__ = ["AnomalyDetector"]

import statistics
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.value_objects.dq_anomaly import (
    DQAnomaly,
    DQAnomalySeverity,
    DQAnomalyType,
)
from bioetl.infrastructure.observability.anomaly.detectors.zscore import ZScoreDetector

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.infrastructure.observability.anomaly.detectors.base import (
        DetectorStrategy,
    )


class AnomalyDetector:
    """Statistical anomaly detection with pluggable strategies.

    Attributes:
        baseline_window: Number of historical data points for baseline
        threshold: Detection threshold (interpretation depends on strategy)
        min_baseline_samples: Minimum samples required for detection
        strategy: Detection algorithm (default: ZScoreDetector)

    """

    def __init__(
        self,
        baseline_window: int = 7,
        z_score_threshold: float = 2.0,
        min_baseline_samples: int = 3,
        strategy: DetectorStrategy | None = None,
    ) -> None:
        """Initialize anomaly detector."""
        if baseline_window < 1:
            raise ValueError("baseline_window must be >= 1")
        if z_score_threshold < 0:
            raise ValueError("z_score_threshold must be >= 0")
        if min_baseline_samples < 1:
            raise ValueError("min_baseline_samples must be >= 1")

        self.baseline_window = baseline_window
        self.z_score_threshold = z_score_threshold
        self.min_baseline_samples = min_baseline_samples
        self.strategy = strategy or ZScoreDetector()

        self._baselines: dict[str, list[float]] = {}
        self._thresholds: dict[str, tuple[float, float]] = {}

    def update_baseline(self, metric_name: str, values: Sequence[float]) -> None:
        """Update baseline with historical data.

        Args:
            metric_name: Name of the metric.
            values: Collection of values.
        """
        if not values:
            return
        if metric_name not in self._baselines:
            self._baselines[metric_name] = []

        baseline = self._baselines[metric_name]
        baseline.extend(values)

        if len(baseline) > self.baseline_window:
            self._baselines[metric_name] = baseline[-self.baseline_window :]

    def add_baseline_value(self, metric_name: str, value: float) -> None:
        """Add single value to baseline.

        Args:
            metric_name: Name of the metric.
            value: Input value.
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
            metric_name: Name of the metric.
            min_value: Minimum value.
            max_value: Maximum value.
        """
        min_val = min_value if min_value is not None else float("-inf")
        max_val = max_value if max_value is not None else float("inf")

        if min_val > max_val:
            raise ValueError("min_value must be <= max_value")

        self._thresholds[metric_name] = (min_val, max_val)

    def detect(
        self, metric_name: str, current_value: float, timestamp: datetime | None = None
    ) -> DQAnomaly | None:
        """Detect anomaly in current value.

        Args:
            metric_name: Name of metric being analyzed
            current_value: Current observed value
            timestamp: Timestamp for the anomaly (should be created in application layer)

        Returns:
            Typed domain anomaly if detected, None otherwise.
        """
        if anomaly := self._check_thresholds(metric_name, current_value, timestamp):
            return anomaly

        baseline = self._baselines.get(metric_name, [])
        if len(baseline) < self.min_baseline_samples:
            return None

        if timestamp is None:
            return None  # No anomaly without timestamp from application layer

        return self.strategy.detect(
            metric_name, current_value, baseline, self.z_score_threshold, timestamp
        )

    def _check_thresholds(
        self, metric_name: str, current_value: float, timestamp: datetime | None = None
    ) -> DQAnomaly | None:
        """Check if the current value exceeds configured thresholds.

        Returns:
            Typed domain anomaly if a configured threshold is exceeded, None otherwise.
        """
        if metric_name not in self._thresholds:
            return None
        if timestamp is None:
            return None  # No anomaly without timestamp from application layer

        min_val, max_val = self._thresholds[metric_name]
        if min_val <= current_value <= max_val:
            return None

        return self._create_threshold_anomaly(
            metric_name, current_value, min_val, max_val, timestamp
        )

    def _create_threshold_anomaly(
        self,
        metric_name: str,
        current_value: float,
        min_val: float,
        max_val: float,
        timestamp: datetime,
    ) -> DQAnomaly:
        """Create anomaly for threshold breach.

        Returns:
            Typed domain anomaly with threshold-exceeded semantics.
        """
        # Avoid arithmetic on infinities for one-sided thresholds.
        min_finite = min_val if min_val != float("-inf") else None
        max_finite = max_val if max_val != float("inf") else None
        if min_finite is not None and max_finite is not None:
            baseline_mean = (min_finite + max_finite) / 2
            span = max_finite - min_finite
            baseline_stddev = span / 4 if span > 0 else 0.0
        elif max_finite is not None:
            baseline_mean = max_finite
            baseline_stddev = 0.0
        elif min_finite is not None:
            baseline_mean = min_finite
            baseline_stddev = 0.0
        else:
            baseline_mean = current_value
            baseline_stddev = 0.0

        if baseline_stddev > 0:
            z_score = abs(current_value - baseline_mean) / baseline_stddev
        else:
            # One-sided or zero-width threshold: treat breach as critical distance.
            z_score = 10.0

        if current_value < min_val:
            message = f"Value {current_value:.2f} below minimum threshold {min_val:.2f}"
        else:
            message = (
                f"Value {current_value:.2f} exceeds maximum threshold {max_val:.2f}"
            )

        return DQAnomaly(
            metric_name=metric_name,
            current_value=current_value,
            baseline_mean=baseline_mean,
            baseline_stddev=baseline_stddev,
            anomaly_type=DQAnomalyType.THRESHOLD_EXCEEDED,
            severity=DQAnomalySeverity.CRITICAL,
            z_score=z_score,
            timestamp=timestamp,
            message=message,
        )

    def clear_baseline(self, metric_name: str) -> None:
        """Clear baseline for a metric.

        Args:
            metric_name: Name of the metric.
        """
        self._baselines.pop(metric_name, None)

    def get_baseline_stats(self, metric_name: str) -> tuple[float, float, int] | None:
        """Get baseline statistics (mean, stddev, count) for a metric.

        Args:
            metric_name: Name of the metric.

        Returns:
            Baseline stats.
        """
        baseline = self._baselines.get(metric_name)
        if not baseline:
            return None

        mean = statistics.mean(baseline)
        stddev = statistics.stdev(baseline) if len(baseline) >= 2 else 0.0

        return (mean, stddev, len(baseline))
