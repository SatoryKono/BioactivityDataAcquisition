"""IQR (Interquartile Range) based anomaly detection.

Uses quartiles to identify outliers, robust to non-normal distributions.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from datetime import UTC, datetime

from bioetl.infrastructure.observability.anomaly.detectors.base import DetectorStrategy
from bioetl.infrastructure.observability.anomaly.types import (
    Anomaly,
    AnomalySeverity,
    AnomalyType,
)


class IQRDetector(DetectorStrategy):
    """IQR-based anomaly detection.

    Uses interquartile range (Q3 - Q1) to identify outliers.
    More robust than Z-score for non-normal distributions.

    IQR multiplier thresholds:
    - score > 1.5: Low severity (mild outlier)
    - score > 2.5: Medium severity
    - score > 3.5: High severity
    - score > 5.0: Critical severity
    """

    MIN_SAMPLES = 4

    def detect(
        self,
        metric_name: str,
        current_value: float,
        baseline: Sequence[float],
        threshold: float = 1.5,
    ) -> Anomaly | None:
        """Detect anomaly using IQR method."""
        if len(baseline) < self.MIN_SAMPLES:
            return None

        q1, q3 = self._calculate_quartiles(baseline)
        iqr = q3 - q1

        if iqr == 0:
            return None

        score = self._calculate_iqr_score(current_value, q1, q3, iqr)
        if score < threshold:
            return None

        mean = statistics.mean(baseline)
        stddev = statistics.stdev(baseline) if len(baseline) >= 2 else 0.0
        return self._create_anomaly(metric_name, current_value, mean, stddev, score)

    def _calculate_quartiles(self, data: Sequence[float]) -> tuple[float, float]:
        """Calculate Q1 and Q3 quartiles."""
        sorted_data = sorted(data)
        n = len(sorted_data)
        q1_idx = n // 4
        q3_idx = (3 * n) // 4
        return sorted_data[q1_idx], sorted_data[q3_idx]

    def _calculate_iqr_score(
        self, value: float, q1: float, q3: float, iqr: float
    ) -> float:
        """Calculate IQR multiplier for a value."""
        if value < q1:
            return (q1 - value) / iqr
        if value > q3:
            return (value - q3) / iqr
        return 0.0

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
            f"is {score:.2f} IQR from quartile bounds"
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
        """Map IQR multiplier to severity level."""
        if score >= 5.0:
            return AnomalySeverity.CRITICAL
        if score >= 3.5:
            return AnomalySeverity.HIGH
        if score >= 2.5:
            return AnomalySeverity.MEDIUM
        return AnomalySeverity.LOW
