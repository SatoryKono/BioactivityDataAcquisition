"""MAD (Median Absolute Deviation) based anomaly detection.

Uses median and MAD for robust outlier detection.
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


class MADDetector(DetectorStrategy):
    """MAD-based anomaly detection.

    Uses Median Absolute Deviation for robust outlier detection.
    More robust than Z-score and IQR for skewed distributions.

    Modified Z-score thresholds:
    - score > 2.0: Low severity
    - score > 3.0: Medium severity
    - score > 4.0: High severity
    - score > 5.0: Critical severity
    """

    MIN_SAMPLES = 3
    CONSISTENCY_CONSTANT = 1.4826  # For normal distribution

    def detect(
        self,
        metric_name: str,
        current_value: float,
        baseline: Sequence[float],
        threshold: float = 2.0,
    ) -> Anomaly | None:
        """Detect anomaly using MAD method."""
        if len(baseline) < self.MIN_SAMPLES:
            return None

        median = statistics.median(baseline)
        mad = self._calculate_mad(baseline, median)

        if mad == 0:
            return None

        score = self._calculate_modified_zscore(current_value, median, mad)
        if score < threshold:
            return None

        mean = statistics.mean(baseline)
        stddev = statistics.stdev(baseline) if len(baseline) >= 2 else 0.0
        return self._create_anomaly(metric_name, current_value, mean, stddev, score)

    def _calculate_mad(self, data: Sequence[float], median: float) -> float:
        """Calculate Median Absolute Deviation."""
        deviations = [abs(x - median) for x in data]
        return statistics.median(deviations) * self.CONSISTENCY_CONSTANT

    def _calculate_modified_zscore(
        self, value: float, median: float, mad: float
    ) -> float:
        """Calculate modified Z-score using MAD."""
        return abs(value - median) / mad

    def _create_anomaly(
        self,
        metric_name: str,
        current_value: float,
        mean: float,
        stddev: float,
        score: float,
    ) -> Anomaly:
        """Create Anomaly object from detection results."""
        anomaly_type = AnomalyType.SPIKE if current_value > mean else AnomalyType.DROP
        severity = self.get_severity(score)
        message = (
            f"{anomaly_type.value.capitalize()} detected: value {current_value:.2f} "
            f"has modified Z-score of {score:.2f}"
        )

        return Anomaly(
            metric_name=metric_name,
            current_value=current_value,
            baseline_mean=mean,
            baseline_stddev=stddev,
            anomaly_type=anomaly_type,
            severity=severity,
            z_score=score,
            timestamp=datetime.now(UTC),
            message=message,
        )

    def get_severity(self, score: float) -> AnomalySeverity:
        """Map modified Z-score to severity level."""
        if score >= 5.0:
            return AnomalySeverity.CRITICAL
        if score >= 4.0:
            return AnomalySeverity.HIGH
        if score >= 3.0:
            return AnomalySeverity.MEDIUM
        return AnomalySeverity.LOW
