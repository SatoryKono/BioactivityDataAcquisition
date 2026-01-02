"""Alert channels for sending notifications."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.observability.alerting.types import Alert


class AlertChannel(ABC):
    """Base class for alert channels."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Channel name for configuration."""
        ...

    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """Send alert through this channel.

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully, False otherwise

        """
        ...


class LoggerAlertChannel(AlertChannel):
    """Alert channel that logs alerts using structured logging."""

    def __init__(self, logger: LoggerPort) -> None:
        """Initialize logger channel.

        Args:
            logger: Logger port for structured logging

        """
        self._logger = logger

    @property
    def name(self) -> str:
        """Channel name."""
        return "logger"

    async def send(self, alert: Alert) -> bool:
        """Log alert with structured logging."""
        self._logger.warning(
            "anomaly_alert",
            alert_id=alert.id,
            alert_severity=alert.severity.value,
            alert_title=alert.title,
            pipeline=alert.pipeline,
            metric_name=alert.anomaly.metric_name,
            anomaly_type=alert.anomaly.anomaly_type.value,
            current_value=alert.anomaly.current_value,
            baseline_mean=alert.anomaly.baseline_mean,
            z_score=alert.anomaly.z_score,
        )
        return True


class WebhookAlertChannel(AlertChannel):
    """Alert channel that sends alerts to a webhook URL."""

    def __init__(
        self,
        url: str,
        logger: LoggerPort,
        timeout: float = 10.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize webhook channel.

        Args:
            url: Webhook URL to POST alerts to
            logger: Logger for error logging
            timeout: Request timeout in seconds
            http_client: Optional httpx client (for DI)

        """
        self._url = url
        self._logger = logger
        self._timeout = timeout
        self._client = http_client
        self._owns_client = http_client is None

    @property
    def name(self) -> str:
        """Channel name."""
        return "webhook"

    async def send(self, alert: Alert) -> bool:
        """Send alert to webhook URL.

        Payload format is compatible with Slack incoming webhooks.
        Customize the payload format for other services.
        """
        import httpx

        client = self._client or httpx.AsyncClient(timeout=self._timeout)

        try:
            # Format for Slack-compatible webhook
            payload = self._format_slack_payload(alert)

            response = await client.post(
                self._url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code >= 400:
                self._logger.error(
                    "webhook_alert_failed",
                    status_code=response.status_code,
                    alert_id=alert.id,
                )
                return False

            self._logger.debug(
                "webhook_alert_sent",
                alert_id=alert.id,
                status_code=response.status_code,
            )
            return True

        except httpx.RequestError as e:
            self._logger.error(
                "webhook_alert_error",
                error=str(e),
                alert_id=alert.id,
            )
            return False
        finally:
            if self._owns_client:
                await client.aclose()

    def _format_slack_payload(self, alert: Alert) -> dict:
        """Format alert as Slack-compatible payload."""
        severity_emoji = {
            "info": ":information_source:",
            "warning": ":warning:",
            "error": ":x:",
            "critical": ":rotating_light:",
        }

        emoji = severity_emoji.get(alert.severity.value, ":bell:")

        return {
            "text": f"{emoji} *{alert.title}*",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} {alert.title}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Pipeline:*\n{alert.pipeline}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Severity:*\n{alert.severity.value.upper()}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Metric:*\n{alert.anomaly.metric_name}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Value:*\n{alert.anomaly.current_value:.2f}",
                        },
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Details:*\n{alert.message}",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Baseline: {alert.anomaly.baseline_mean:.2f} ± {alert.anomaly.baseline_stddev:.2f} | Z-score: {alert.anomaly.z_score:.2f}",
                        },
                    ],
                },
            ],
        }


class CompositeAlertChannel(AlertChannel):
    """Channel that sends alerts to multiple channels."""

    def __init__(self, channels: list[AlertChannel]) -> None:
        """Initialize composite channel.

        Args:
            channels: List of channels to send to

        """
        self._channels = channels

    @property
    def name(self) -> str:
        """Channel name."""
        return "composite"

    async def send(self, alert: Alert) -> bool:
        """Send alert to all channels.

        Returns True if at least one channel succeeded.
        """
        results = []
        for channel in self._channels:
            try:
                result = await channel.send(alert)
                results.append(result)
            except Exception:
                results.append(False)

        return any(results)
