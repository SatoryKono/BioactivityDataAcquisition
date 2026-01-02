"""Tests for anomaly alerting service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.observability.alerting import (
    Alert,
    AlertConfig,
    AlertRule,
    AlertService,
    AlertSeverity,
    LoggerAlertChannel,
    WebhookAlertChannel,
)
from bioetl.infrastructure.observability.anomaly.types import (
    Anomaly,
    AnomalySeverity,
    AnomalyType,
)


@pytest.fixture
def sample_anomaly() -> Anomaly:
    """Create a sample anomaly for testing."""
    return Anomaly(
        metric_name="record_count",
        current_value=500.0,
        baseline_mean=1000.0,
        baseline_stddev=50.0,
        anomaly_type=AnomalyType.DROP,
        severity=AnomalySeverity.CRITICAL,
        z_score=10.0,
        timestamp=datetime.now(tz=UTC),
        message="Record count dropped significantly",
    )


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    logger = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    return logger


class TestAlertSeverity:
    """Tests for AlertSeverity enum."""

    def test_severity_values(self) -> None:
        """Test severity enum has expected values."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestAlert:
    """Tests for Alert dataclass."""

    def test_to_dict(self, sample_anomaly: Anomaly) -> None:
        """Test alert serialization to dict."""
        alert = Alert(
            id="test123",
            anomaly=sample_anomaly,
            severity=AlertSeverity.CRITICAL,
            title="Test Alert",
            message="Test message",
            pipeline="test_pipeline",
            timestamp=datetime.now(tz=UTC),
        )

        data = alert.to_dict()

        assert data["id"] == "test123"
        assert data["severity"] == "critical"
        assert data["title"] == "Test Alert"
        assert data["pipeline"] == "test_pipeline"
        assert "anomaly" in data
        assert data["anomaly"]["metric_name"] == "record_count"


class TestAlertConfig:
    """Tests for AlertConfig."""

    def test_default_config(self) -> None:
        """Test default configuration has sensible rules."""
        config = AlertConfig.default()

        assert config.enabled is True
        assert len(config.rules) > 0
        assert "logger" in config.default_channels

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = AlertConfig(
            enabled=True,
            rules=[
                AlertRule(
                    name="custom_rule",
                    min_severity="high",
                    alert_severity=AlertSeverity.ERROR,
                )
            ],
            webhook_url="https://example.com/webhook",
        )

        assert len(config.rules) == 1
        assert config.webhook_url == "https://example.com/webhook"


class TestLoggerAlertChannel:
    """Tests for LoggerAlertChannel."""

    @pytest.mark.asyncio
    async def test_send_logs_alert(
        self, sample_anomaly: Anomaly, mock_logger: MagicMock
    ) -> None:
        """Test that sending alert logs structured message."""
        channel = LoggerAlertChannel(mock_logger)
        alert = Alert(
            id="test123",
            anomaly=sample_anomaly,
            severity=AlertSeverity.CRITICAL,
            title="Test Alert",
            message="Test message",
            pipeline="test_pipeline",
            timestamp=datetime.now(tz=UTC),
        )

        result = await channel.send(alert)

        assert result is True
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args.kwargs
        assert call_kwargs["alert_id"] == "test123"
        assert call_kwargs["pipeline"] == "test_pipeline"


class TestWebhookAlertChannel:
    """Tests for WebhookAlertChannel."""

    @pytest.mark.asyncio
    async def test_send_webhook_success(
        self, sample_anomaly: Anomaly, mock_logger: MagicMock
    ) -> None:
        """Test successful webhook send."""
        # Create mock HTTP client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_response)

        channel = WebhookAlertChannel(
            url="https://example.com/webhook",
            logger=mock_logger,
            http_client=mock_client,
        )

        alert = Alert(
            id="test123",
            anomaly=sample_anomaly,
            severity=AlertSeverity.CRITICAL,
            title="Test Alert",
            message="Test message",
            pipeline="test_pipeline",
            timestamp=datetime.now(tz=UTC),
        )

        result = await channel.send(alert)

        assert result is True
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_webhook_failure(
        self, sample_anomaly: Anomaly, mock_logger: MagicMock
    ) -> None:
        """Test webhook failure handling."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client.post = AsyncMock(return_value=mock_response)

        channel = WebhookAlertChannel(
            url="https://example.com/webhook",
            logger=mock_logger,
            http_client=mock_client,
        )

        alert = Alert(
            id="test123",
            anomaly=sample_anomaly,
            severity=AlertSeverity.CRITICAL,
            title="Test Alert",
            message="Test message",
            pipeline="test_pipeline",
            timestamp=datetime.now(tz=UTC),
        )

        result = await channel.send(alert)

        assert result is False
        mock_logger.error.assert_called()


class TestAlertService:
    """Tests for AlertService."""

    @pytest.mark.asyncio
    async def test_alert_creates_and_dispatches(
        self, sample_anomaly: Anomaly, mock_logger: MagicMock
    ) -> None:
        """Test that alert service creates and dispatches alerts."""
        service = AlertService(
            logger=mock_logger,
            config=AlertConfig.default(),
        )

        alert = await service.alert(sample_anomaly, pipeline="test_pipeline")

        assert alert is not None
        assert alert.pipeline == "test_pipeline"
        assert alert.anomaly == sample_anomaly
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_alert_respects_disabled_config(
        self, sample_anomaly: Anomaly, mock_logger: MagicMock
    ) -> None:
        """Test that disabled config prevents alerting."""
        config = AlertConfig(enabled=False)
        service = AlertService(
            logger=mock_logger,
            config=config,
        )

        alert = await service.alert(sample_anomaly, pipeline="test_pipeline")

        assert alert is None

    @pytest.mark.asyncio
    async def test_alert_respects_cooldown(
        self, sample_anomaly: Anomaly, mock_logger: MagicMock
    ) -> None:
        """Test that cooldown prevents duplicate alerts."""
        config = AlertConfig(
            enabled=True,
            rules=[
                AlertRule(
                    name="test_rule",
                    min_severity="low",
                    alert_severity=AlertSeverity.WARNING,
                    cooldown_seconds=300,  # 5 minutes
                )
            ],
        )
        service = AlertService(
            logger=mock_logger,
            config=config,
        )

        # First alert should succeed
        alert1 = await service.alert(sample_anomaly, pipeline="test_pipeline")
        assert alert1 is not None

        # Second alert should be skipped (cooldown)
        alert2 = await service.alert(sample_anomaly, pipeline="test_pipeline")
        assert alert2 is None

    @pytest.mark.asyncio
    async def test_alert_batch(
        self, sample_anomaly: Anomaly, mock_logger: MagicMock
    ) -> None:
        """Test batch alerting."""
        service = AlertService(
            logger=mock_logger,
            config=AlertConfig.default(),
        )

        # Create multiple anomalies with different metrics
        anomaly2 = Anomaly(
            metric_name="error_rate",
            current_value=0.5,
            baseline_mean=0.05,
            baseline_stddev=0.02,
            anomaly_type=AnomalyType.SPIKE,
            severity=AnomalySeverity.HIGH,
            z_score=22.5,
            timestamp=datetime.now(tz=UTC),
            message="Error rate spiked",
        )

        alerts = await service.alert_batch(
            [sample_anomaly, anomaly2],
            pipeline="test_pipeline",
        )

        assert len(alerts) == 2

    def test_add_remove_channel(self, mock_logger: MagicMock) -> None:
        """Test adding and removing channels."""
        service = AlertService(logger=mock_logger)

        # Logger channel is always present
        assert "logger" in service.channel_names

        # Add custom channel
        custom_channel = LoggerAlertChannel(mock_logger)
        custom_channel._name = "custom"  # type: ignore

        class CustomChannel(LoggerAlertChannel):
            @property
            def name(self) -> str:
                return "custom"

        service.add_channel(CustomChannel(mock_logger))
        assert "custom" in service.channel_names

        # Remove channel
        service.remove_channel("custom")
        assert "custom" not in service.channel_names
