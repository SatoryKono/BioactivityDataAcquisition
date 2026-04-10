"""Domain DTOs for data-quality anomaly detection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

__all__ = ["DQAnomaly", "DQAnomalySeverity", "DQAnomalyType"]


class DQAnomalyType(StrEnum):
    """Types of data-quality anomalies surfaced through the DQ monitor port."""

    SPIKE = "spike"
    DROP = "drop"
    THRESHOLD_EXCEEDED = "threshold_exceeded"
    TREND_CHANGE = "trend_change"


class DQAnomalySeverity(StrEnum):
    """Severity levels for DQ anomalies."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class DQAnomaly:
    """Immutable domain representation of one detected DQ anomaly."""

    metric_name: str
    current_value: float
    baseline_mean: float
    baseline_stddev: float
    anomaly_type: DQAnomalyType
    severity: DQAnomalySeverity
    z_score: float
    timestamp: datetime
    message: str

    def __str__(self) -> str:
        """Format anomaly for logs and operator-facing messages."""
        return (
            f"[{self.severity.value.upper()}] {self.anomaly_type.value} in "
            f"{self.metric_name}: current={self.current_value:.2f}, "
            f"baseline={self.baseline_mean:.2f}±{self.baseline_stddev:.2f} "
            f"(z-score={self.z_score:.2f})"
        )
