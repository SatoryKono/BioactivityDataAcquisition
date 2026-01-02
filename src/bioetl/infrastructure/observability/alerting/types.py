"""Alert types and configuration for anomaly alerting."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.infrastructure.observability.anomaly.types import Anomaly


class AlertSeverity(str, Enum):
    """Alert severity levels for routing and filtering."""

    INFO = "info"  # Low priority, informational
    WARNING = "warning"  # Medium priority, needs attention
    ERROR = "error"  # High priority, action required
    CRITICAL = "critical"  # Critical, immediate action required


@dataclass(frozen=True)
class Alert:
    """Alert generated from an anomaly.

    Attributes:
        id: Unique alert identifier
        anomaly: Source anomaly that triggered this alert
        severity: Alert severity level
        title: Short alert title
        message: Detailed alert message
        pipeline: Pipeline where anomaly occurred
        timestamp: When alert was created
        metadata: Additional context for routing/display

    """

    id: str
    anomaly: Anomaly
    severity: AlertSeverity
    title: str
    message: str
    pipeline: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert alert to dictionary for serialization."""
        return {
            "id": self.id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "pipeline": self.pipeline,
            "timestamp": self.timestamp.isoformat(),
            "anomaly": {
                "metric_name": self.anomaly.metric_name,
                "current_value": self.anomaly.current_value,
                "baseline_mean": self.anomaly.baseline_mean,
                "baseline_stddev": self.anomaly.baseline_stddev,
                "anomaly_type": self.anomaly.anomaly_type.value,
                "z_score": self.anomaly.z_score,
            },
            "metadata": self.metadata,
        }


@dataclass
class AlertRule:
    """Rule for generating alerts from anomalies.

    Attributes:
        name: Rule name for identification
        metric_pattern: Pattern to match metric names (supports wildcards)
        min_severity: Minimum anomaly severity to trigger alert
        alert_severity: Severity level for generated alerts
        channels: List of channel names to send alerts to
        cooldown_seconds: Minimum time between alerts for same metric

    """

    name: str
    metric_pattern: str = "*"  # Matches all metrics
    min_severity: str = "low"  # Minimum anomaly severity
    alert_severity: AlertSeverity = AlertSeverity.WARNING
    channels: list[str] = field(default_factory=lambda: ["logger"])
    cooldown_seconds: int = 300  # 5 minutes default


@dataclass
class AlertConfig:
    """Configuration for alert service.

    Attributes:
        enabled: Whether alerting is enabled
        rules: List of alert rules
        default_channels: Default channels if rule doesn't specify
        webhook_url: Optional webhook URL for external alerting
        webhook_timeout: Timeout for webhook requests in seconds

    """

    enabled: bool = True
    rules: list[AlertRule] = field(default_factory=list)
    default_channels: list[str] = field(default_factory=lambda: ["logger"])
    webhook_url: str | None = None
    webhook_timeout: float = 10.0

    @classmethod
    def default(cls) -> AlertConfig:
        """Create default configuration."""
        return cls(
            enabled=True,
            rules=[
                AlertRule(
                    name="critical_anomalies",
                    min_severity="critical",
                    alert_severity=AlertSeverity.CRITICAL,
                    channels=["logger", "webhook"],
                ),
                AlertRule(
                    name="high_anomalies",
                    min_severity="high",
                    alert_severity=AlertSeverity.ERROR,
                    channels=["logger"],
                ),
                AlertRule(
                    name="medium_anomalies",
                    min_severity="medium",
                    alert_severity=AlertSeverity.WARNING,
                    channels=["logger"],
                ),
            ],
        )
