"""Anomaly alerting module for BioETL.

Provides alerting capabilities when anomalies are detected in data quality metrics.

Supported channels:
- Logger: Structured logging of alerts
- Webhook: HTTP POST to external services (Slack, PagerDuty, etc.)

Usage:
    from bioetl.infrastructure.observability.alerting import AlertService

    # Create alerting service with webhook
    service = AlertService(
        logger=my_logger,
        channels=[
            WebhookAlertChannel(url="https://hooks.slack.com/...", logger=my_logger)
        ]
    )

    # Send alert for an anomaly
    await service.alert(anomaly)
"""

from __future__ import annotations

from bioetl.infrastructure.observability.alerting.channels import (
    AlertChannel,
    LoggerAlertChannel,
    WebhookAlertChannel,
)
from bioetl.infrastructure.observability.alerting.service import AlertService
from bioetl.infrastructure.observability.alerting.types import (
    Alert,
    AlertConfig,
    AlertRule,
    AlertSeverity,
)

__all__ = [
    "Alert",
    "AlertChannel",
    "AlertConfig",
    "AlertRule",
    "AlertService",
    "AlertSeverity",
    "LoggerAlertChannel",
    "WebhookAlertChannel",
]
