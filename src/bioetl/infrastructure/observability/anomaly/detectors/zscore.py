"""Z-score based anomaly detection.

Uses standard deviation to identify outliers.
"""

from __future__ import annotations

__all__ = ["ZScoreDetector"]

import statistics
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.value_objects.dq_anomaly import (
    DQAnomaly,
    DQAnomalySeverity,
    DQAnomalyType,
)
from bioetl.infrastructure.observability.anomaly.detectors.base import DetectorStrategy

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
        timestamp: datetime | None = None,
    ) -> DQAnomaly | None:
        """Detect anomaly using Z-score method.

        Args:
            metric_name: Name of the metric.
            current_value: Current value.
            baseline: Baseline.
            threshold: Threshold value.
            timestamp: Timestamp.

        Returns:
            The typed domain anomaly result, if any.
        """
        if len(baseline) < self.MIN_SAMPLES:
            return None
        if timestamp is None:
            return None  # No anomaly without timestamp from application layer

        mean = statistics.mean(baseline)
        stddev = statistics.stdev(baseline)

        z_score = self._calculate_z_score(current_value, mean, stddev)
        if z_score is None or z_score < threshold:
            return None

        return self._create_anomaly(
            metric_name, current_value, mean, stddev, z_score, timestamp
        )

    def _calculate_z_score(
        self, value: float, mean: float, stddev: float
    ) -> float | None:
        """Calculate Z-score for a value.

        Returns:
            Z-score float if calculable, None if standard deviation is zero and deviation is below threshold.
        """
        if stddev == 0:
            # Constant baseline: any value differing from the constant mean is an
            # anomaly. Use a documented high severity score (maps to CRITICAL via
            # get_severity thresholds > 5).
            if value == mean:
                return None
            return 10.0
        return abs(value - mean) / stddev

    def _create_anomaly(
        self,
        metric_name: str,
        current_value: float,
        mean: float,
        stddev: float,
        z_score: float,
        timestamp: datetime,
    ) -> DQAnomaly:
        """Create a typed anomaly DTO from detection results.

        Returns:
            Typed domain anomaly with SPIKE or DROP type based on deviation direction.
        """
        anomaly_type = (
            DQAnomalyType.SPIKE if current_value > mean else DQAnomalyType.DROP
        )
        severity = self.get_severity(z_score)
        message = (
            f"{anomaly_type.value.capitalize()} detected: value {current_value:.2f} is "
            f"{z_score:.2f} std deviations from baseline mean {mean:.2f}"
        )

        return DQAnomaly(
            metric_name=metric_name,
            current_value=current_value,
            baseline_mean=mean,
            baseline_stddev=stddev,
            anomaly_type=anomaly_type,
            severity=severity,
            z_score=z_score,
            timestamp=timestamp,
            message=message,
        )

    def get_severity(self, score: float) -> DQAnomalySeverity:
        """Map Z-score to severity level.

        Args:
            score: Score.

        Returns:
            Severity.
        """
        if score >= 5.0:
            return DQAnomalySeverity.CRITICAL
        if score >= 4.0:
            return DQAnomalySeverity.HIGH
        if score >= 3.0:
            return DQAnomalySeverity.MEDIUM
        return DQAnomalySeverity.LOW
