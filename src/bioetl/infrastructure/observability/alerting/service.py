"""Alert service for managing and dispatching anomaly alerts."""

from __future__ import annotations

import fnmatch
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.infrastructure.observability.alerting.channels import (
    AlertChannel,
    LoggerAlertChannel,
)
from bioetl.infrastructure.observability.alerting.types import (
    Alert,
    AlertConfig,
    AlertRule,
    AlertSeverity,
)
from bioetl.infrastructure.observability.anomaly.types import Anomaly, AnomalySeverity

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


# Map anomaly severity to alert severity
SEVERITY_MAP: dict[AnomalySeverity, AlertSeverity] = {
    AnomalySeverity.LOW: AlertSeverity.INFO,
    AnomalySeverity.MEDIUM: AlertSeverity.WARNING,
    AnomalySeverity.HIGH: AlertSeverity.ERROR,
    AnomalySeverity.CRITICAL: AlertSeverity.CRITICAL,
}


class AlertService:
    """Service for generating and dispatching alerts from anomalies.

    Manages alert channels, rules, and cooldown to prevent alert fatigue.

    Usage:
        service = AlertService(
            logger=my_logger,
            config=AlertConfig.default(),
        )

        # Process an anomaly
        await service.alert(anomaly, pipeline="chembl_activity")

        # Or integrate with DataQualityMonitor
        anomalies = monitor.check_quality(metrics)
        for anomaly in anomalies:
            await service.alert(anomaly, pipeline=pipeline_name)

    """

    def __init__(
        self,
        logger: LoggerPort,
        config: AlertConfig | None = None,
        channels: list[AlertChannel] | None = None,
    ) -> None:
        """Initialize alert service.

        Args:
            logger: Logger port for structured logging
            config: Alert configuration (uses default if not provided)
            channels: Optional list of alert channels

        """
        self._logger = logger
        self._config = config or AlertConfig.default()
        self._channels: dict[str, AlertChannel] = {}
        self._last_alert_times: dict[str, datetime] = {}  # metric -> last alert time

        # Always add logger channel
        self._channels["logger"] = LoggerAlertChannel(logger)

        # Add provided channels
        if channels:
            for channel in channels:
                self._channels[channel.name] = channel

    def add_channel(self, channel: AlertChannel) -> None:
        """Add an alert channel.

        Args:
            channel: Channel to add

        """
        self._channels[channel.name] = channel

    def remove_channel(self, name: str) -> None:
        """Remove an alert channel.

        Args:
            name: Name of channel to remove

        """
        self._channels.pop(name, None)

    async def alert(
        self,
        anomaly: Anomaly,
        pipeline: str,
        metadata: dict | None = None,
    ) -> Alert | None:
        """Generate and dispatch an alert for an anomaly.

        Args:
            anomaly: Detected anomaly
            pipeline: Pipeline name where anomaly occurred
            metadata: Optional additional context

        Returns:
            Generated Alert if sent, None if filtered/skipped

        """
        if not self._config.enabled:
            return None

        # Find matching rule
        rule = self._find_matching_rule(anomaly)
        if not rule:
            return None

        # Check cooldown
        if not self._check_cooldown(anomaly.metric_name, rule.cooldown_seconds):
            self._logger.debug(
                "alert_skipped_cooldown",
                metric_name=anomaly.metric_name,
                cooldown_seconds=rule.cooldown_seconds,
            )
            return None

        # Create alert
        alert = self._create_alert(anomaly, pipeline, rule, metadata)

        # Dispatch to channels
        channels = rule.channels or self._config.default_channels
        await self._dispatch(alert, channels)

        # Update cooldown tracker
        self._last_alert_times[anomaly.metric_name] = datetime.now(tz=UTC)

        return alert

    async def alert_batch(
        self,
        anomalies: list[Anomaly],
        pipeline: str,
        metadata: dict | None = None,
    ) -> list[Alert]:
        """Generate and dispatch alerts for multiple anomalies.

        Args:
            anomalies: List of detected anomalies
            pipeline: Pipeline name
            metadata: Optional additional context

        Returns:
            List of generated alerts

        """
        alerts = []
        for anomaly in anomalies:
            alert = await self.alert(anomaly, pipeline, metadata)
            if alert:
                alerts.append(alert)
        return alerts

    def _find_matching_rule(self, anomaly: Anomaly) -> AlertRule | None:
        """Find first matching rule for an anomaly."""
        severity_order = ["critical", "high", "medium", "low"]
        anomaly_severity_index = severity_order.index(anomaly.severity.value)

        for rule in self._config.rules:
            # Check severity threshold
            rule_severity_index = severity_order.index(rule.min_severity)
            if anomaly_severity_index > rule_severity_index:
                continue

            # Check metric pattern
            if not fnmatch.fnmatch(anomaly.metric_name, rule.metric_pattern):
                continue

            return rule

        return None

    def _check_cooldown(self, metric_name: str, cooldown_seconds: int) -> bool:
        """Check if cooldown period has passed for a metric."""
        last_alert = self._last_alert_times.get(metric_name)
        if not last_alert:
            return True

        elapsed = (datetime.now(tz=UTC) - last_alert).total_seconds()
        return elapsed >= cooldown_seconds

    def _create_alert(
        self,
        anomaly: Anomaly,
        pipeline: str,
        rule: AlertRule,
        metadata: dict | None,
    ) -> Alert:
        """Create an alert from an anomaly."""
        alert_id = str(uuid.uuid4())[:8]

        title = f"Anomaly detected in {pipeline}: {anomaly.metric_name}"
        message = str(anomaly)

        return Alert(
            id=alert_id,
            anomaly=anomaly,
            severity=rule.alert_severity,
            title=title,
            message=message,
            pipeline=pipeline,
            timestamp=datetime.now(tz=UTC),
            metadata=metadata or {},
        )

    async def _dispatch(self, alert: Alert, channel_names: list[str]) -> None:
        """Dispatch alert to specified channels."""
        for name in channel_names:
            channel = self._channels.get(name)
            if not channel:
                self._logger.warning(
                    "alert_channel_not_found",
                    channel_name=name,
                    alert_id=alert.id,
                )
                continue

            try:
                await channel.send(alert)
            except Exception as e:
                self._logger.error(
                    "alert_dispatch_error",
                    channel_name=name,
                    alert_id=alert.id,
                    error=str(e),
                )

    @property
    def config(self) -> AlertConfig:
        """Get current configuration."""
        return self._config

    @property
    def channel_names(self) -> list[str]:
        """Get list of configured channel names."""
        return list(self._channels.keys())
