"""Base types for anomaly detection.

Contains enums and data classes shared across detection strategies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


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
