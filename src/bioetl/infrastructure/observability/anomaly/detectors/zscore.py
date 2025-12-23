"""Z-score based anomaly detection.

Uses standard deviation to identify outliers.
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.infrastructure.observability.anomaly.detectors.base import DetectorStrategy
from bioetl.infrastructure.observability.anomaly.types import (
    Anomaly,
    AnomalySeverity,
    AnomalyType,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class ZScoreDetector(DetectorStrategy):
    """Z-score based anomaly detection.

    Z-score thresholds:
    - score > 2: Low severity
    - score > 3: Medium severity
    - score > 4: High severity
    - score > 5: Critical severity
    """

    MIN_SAMPLES = 2

    def detect(
        self,
        metric_name: str,
        current_value: float,
        baseline: Sequence[float],
        threshold: float = 2.0,
    ) -> Anomaly | None:
        """Detect anomaly using Z-score method."""
        if len(baseline) < self.MIN_SAMPLES:
            return None

        mean = statistics.mean(baseline)
        stddev = statistics.stdev(baseline)

        z_score = self._calculate_z_score(current_value, mean, stddev)
        if z_score is None or z_score < threshold:
            return None

        return self._create_anomaly(metric_name, current_value, mean, stddev, z_score)

    def _calculate_z_score(
        self, value: float, mean: float, stddev: float
    ) -> float | None:
        """Calculate Z-score for a value."""
        if stddev == 0:
            if mean == 0:
                return None
            deviation_pct = abs(value - mean) / abs(mean)
            return deviation_pct * 2 if deviation_pct >= 0.5 else None
        return abs(value - mean) / stddev

    def _create_anomaly(
        self,
        metric_name: str,
        current_value: float,
        mean: float,
        stddev: float,
        z_score: float,
    ) -> Anomaly:
        """Create Anomaly object from detection results."""
        anomaly_type = AnomalyType.SPIKE if current_value > mean else AnomalyType.DROP
        severity = self.get_severity(z_score)
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

    def get_severity(self, score: float) -> AnomalySeverity:
        """Map Z-score to severity level."""
        if score >= 5.0:
            return AnomalySeverity.CRITICAL
        if score >= 4.0:
            return AnomalySeverity.HIGH
        if score >= 3.0:
            return AnomalySeverity.MEDIUM
        return AnomalySeverity.LOW
