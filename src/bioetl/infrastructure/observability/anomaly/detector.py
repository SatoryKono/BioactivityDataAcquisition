"""Anomaly detector with configurable strategy.

Main entry point for anomaly detection functionality.
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.infrastructure.observability.anomaly.detectors.zscore import ZScoreDetector
from bioetl.infrastructure.observability.anomaly.types import (
    Anomaly,
    AnomalySeverity,
    AnomalyType,
)

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
        """Update baseline with historical data."""
        if not values:
            return
        if metric_name not in self._baselines:
            self._baselines[metric_name] = []

        baseline = self._baselines[metric_name]
        baseline.extend(values)

        if len(baseline) > self.baseline_window:
            self._baselines[metric_name] = baseline[-self.baseline_window :]

    def add_baseline_value(self, metric_name: str, value: float) -> None:
        """Add single value to baseline."""
        self.update_baseline(metric_name, [value])

    def set_threshold(
        self,
        metric_name: str,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> None:
        """Set absolute thresholds for a metric."""
        min_val = min_value if min_value is not None else float("-inf")
        max_val = max_value if max_value is not None else float("inf")

        if min_val > max_val:
            raise ValueError("min_value must be <= max_value")

        self._thresholds[metric_name] = (min_val, max_val)

    def detect(self, metric_name: str, current_value: float) -> Anomaly | None:
        """Detect anomaly in current value."""
        if anomaly := self._check_thresholds(metric_name, current_value):
            return anomaly

        baseline = self._baselines.get(metric_name, [])
        if len(baseline) < self.min_baseline_samples:
            return None

        return self.strategy.detect(
            metric_name, current_value, baseline, self.z_score_threshold
        )

    def _check_thresholds(
        self, metric_name: str, current_value: float
    ) -> Anomaly | None:
        """Check if the current value exceeds configured thresholds."""
        if metric_name not in self._thresholds:
            return None

        min_val, max_val = self._thresholds[metric_name]
        if min_val <= current_value <= max_val:
            return None

        return self._create_threshold_anomaly(
            metric_name, current_value, min_val, max_val
        )

    def _create_threshold_anomaly(
        self,
        metric_name: str,
        current_value: float,
        min_val: float,
        max_val: float,
    ) -> Anomaly:
        """Create anomaly for threshold breach."""
        baseline_mean = (min_val + max_val) / 2
        baseline_stddev = (max_val - min_val) / 4

        z_score = (
            abs(current_value - baseline_mean) / baseline_stddev
            if baseline_stddev > 0
            else 10.0
        )

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
        """Clear baseline for a metric."""
        self._baselines.pop(metric_name, None)

    def get_baseline_stats(self, metric_name: str) -> tuple[float, float, int] | None:
        """Get baseline statistics (mean, stddev, count) for a metric."""
        baseline = self._baselines.get(metric_name)
        if not baseline:
            return None

        mean = statistics.mean(baseline)
        stddev = statistics.stdev(baseline) if len(baseline) >= 2 else 0.0

        return (mean, stddev, len(baseline))
