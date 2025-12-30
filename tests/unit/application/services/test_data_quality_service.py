"""Unit tests for the DataQualityService class."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.data_quality_service import DataQualityService
from bioetl.domain.config import DQConfig
from bioetl.domain.exceptions.data_quality import DataQualityThresholdError
from bioetl.domain.value_objects.dq_result import DQResult, DQStatus


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def mock_metrics():
    """Create a mock metrics port."""
    metrics = MagicMock()
    metrics.set_gauge = MagicMock()
    metrics.observe_histogram = MagicMock()
    metrics.increment_counter = MagicMock()
    return metrics


@pytest.fixture
def dq_config():
    """Create a DQ config with default thresholds."""
    return DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20)


@pytest.fixture
def dq_service(mock_logger, mock_metrics, dq_config):
    """Create a DataQualityService instance without dq_monitor."""
    return DataQualityService(
        dq_monitor=None,
        config=dq_config,
        logger=mock_logger,
        metrics=mock_metrics,
        pipeline_name="test_pipeline",
    )


@pytest.mark.unit
class TestDataQualityServiceInit:
    """Tests for DataQualityService initialization."""

    def test_initialization_without_monitor(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test service initializes correctly without dq_monitor."""
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
        )

        assert service._dq_monitor is None
        assert service._config == dq_config
        assert service._logger == mock_logger
        assert service._metrics == mock_metrics
        assert service._pipeline_name == "test_pipeline"

    def test_initialization_with_monitor(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test service initializes correctly with dq_monitor."""
        mock_dq_monitor = MagicMock()

        service = DataQualityService(
            dq_monitor=mock_dq_monitor,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
        )

        assert service._dq_monitor == mock_dq_monitor


@pytest.mark.unit
class TestDataQualityServiceThresholds:
    """Tests for threshold checking in DataQualityService."""

    @pytest.mark.asyncio
    async def test_hard_threshold_exceeded_raises_error(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test that error rate exceeding hard threshold raises DataQualityThresholdError."""
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
        )

        # Metrics with 25% error rate (above hard threshold of 20%)
        metrics = {
            "record_count": 100.0,
            "error_rate": 0.25,
        }

        with pytest.raises(DataQualityThresholdError) as exc_info:
            await service.evaluate(metrics)

        assert exc_info.value.error_rate == 0.25
        assert exc_info.value.threshold == 0.20
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_hard_threshold_exactly_at_limit_raises_error(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test that error rate exactly at hard threshold raises DataQualityThresholdError."""
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
        )

        # Metrics with exactly 20% error rate
        metrics = {
            "record_count": 100.0,
            "error_rate": 0.20,
        }

        with pytest.raises(DataQualityThresholdError):
            await service.evaluate(metrics)

    @pytest.mark.asyncio
    async def test_soft_threshold_exceeded_logs_warning_and_emits_metric(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test that error rate exceeding soft threshold logs warning and emits metric."""
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
        )

        # Metrics with 10% error rate (above soft 5%, below hard 20%)
        metrics = {
            "record_count": 100.0,
            "error_rate": 0.10,
        }

        result = await service.evaluate(metrics)

        assert result.status == DQStatus.WARNING
        assert result.error_rate == 0.10
        mock_logger.warning.assert_called_once()
        mock_metrics.increment_counter.assert_called_once_with(
            "dq_soft_threshold_exceeded",
            1,
            {"pipeline": "test_pipeline"},
        )

    @pytest.mark.asyncio
    async def test_soft_threshold_exactly_at_limit_logs_warning(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test that error rate exactly at soft threshold logs warning."""
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
        )

        # Metrics with exactly 5% error rate
        metrics = {
            "record_count": 100.0,
            "error_rate": 0.05,
        }

        result = await service.evaluate(metrics)

        assert result.status == DQStatus.WARNING
        mock_logger.warning.assert_called_once()
        mock_metrics.increment_counter.assert_called_once()

    @pytest.mark.asyncio
    async def test_below_soft_threshold_passes(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test that error rate below soft threshold passes without warning."""
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
        )

        # Metrics with 3% error rate (below soft threshold)
        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
        }

        result = await service.evaluate(metrics)

        assert result.status == DQStatus.PASSED
        assert result.error_rate == 0.03
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()
        mock_metrics.increment_counter.assert_not_called()


@pytest.mark.unit
class TestDataQualityServiceGracefulDegradation:
    """Tests for graceful degradation without dq_monitor."""

    @pytest.mark.asyncio
    async def test_no_monitor_returns_result_without_anomalies(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test that without dq_monitor, service returns result without anomalies."""
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
        }

        result = await service.evaluate(metrics)

        assert result.anomalies_count == 0
        assert result.has_critical is False
        assert result.check_duration_ms == 0.0
        assert result.anomalies == ()

    @pytest.mark.asyncio
    async def test_no_metrics_port_still_logs_warning(
        self, mock_logger, dq_config
    ):
        """Test that soft threshold logs warning even when metrics port is None."""
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=None,  # No metrics port
            pipeline_name="test_pipeline",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.10,
        }

        result = await service.evaluate(metrics)

        assert result.status == DQStatus.WARNING
        mock_logger.warning.assert_called_once()


@pytest.mark.unit
class TestDataQualityServiceAnomalyDetection:
    """Tests for anomaly detection with dq_monitor."""

    @pytest.mark.asyncio
    async def test_anomaly_detection_with_no_anomalies(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test anomaly detection with no anomalies detected."""
        mock_dq_monitor = MagicMock()
        mock_dq_monitor.check_quality = MagicMock(return_value=[])
        mock_dq_monitor.update_baseline_from_metrics = MagicMock()

        service = DataQualityService(
            dq_monitor=mock_dq_monitor,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
        }

        result = await service.evaluate(metrics)

        assert result.anomalies_count == 0
        assert result.has_critical is False
        mock_dq_monitor.check_quality.assert_called_once_with(metrics)
        mock_dq_monitor.update_baseline_from_metrics.assert_called_once_with(metrics)

    @pytest.mark.asyncio
    async def test_anomaly_detection_with_anomalies(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test anomaly detection with anomalies detected."""
        from bioetl.infrastructure.observability.anomaly.types import (
            Anomaly,
            AnomalySeverity,
            AnomalyType,
        )

        anomaly = Anomaly(
            metric_name="error_rate",
            current_value=0.15,
            baseline_mean=0.05,
            baseline_stddev=0.02,
            anomaly_type=AnomalyType.SPIKE,
            severity=AnomalySeverity.HIGH,
            z_score=5.0,
            timestamp=datetime.now(UTC),
            message="Error rate spike detected",
        )

        mock_dq_monitor = MagicMock()
        mock_dq_monitor.check_quality = MagicMock(return_value=[anomaly])
        mock_dq_monitor.update_baseline_from_metrics = MagicMock()

        service = DataQualityService(
            dq_monitor=mock_dq_monitor,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
        }

        result = await service.evaluate(metrics)

        assert result.anomalies_count == 1
        assert result.has_critical is False
        assert len(result.anomalies) == 1
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_anomaly_detection_with_critical_anomaly(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test anomaly detection with critical anomaly."""
        from bioetl.infrastructure.observability.anomaly.types import (
            Anomaly,
            AnomalySeverity,
            AnomalyType,
        )

        critical_anomaly = Anomaly(
            metric_name="error_rate",
            current_value=0.50,
            baseline_mean=0.05,
            baseline_stddev=0.02,
            anomaly_type=AnomalyType.THRESHOLD_EXCEEDED,
            severity=AnomalySeverity.CRITICAL,
            z_score=22.5,
            timestamp=datetime.now(UTC),
            message="Error rate critical",
        )

        mock_dq_monitor = MagicMock()
        mock_dq_monitor.check_quality = MagicMock(return_value=[critical_anomaly])
        mock_dq_monitor.update_baseline_from_metrics = MagicMock()

        service = DataQualityService(
            dq_monitor=mock_dq_monitor,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
        }

        result = await service.evaluate(metrics)

        assert result.anomalies_count == 1
        assert result.has_critical is True
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_check_duration_metric_emitted(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test that check duration metric is emitted."""
        mock_dq_monitor = MagicMock()
        mock_dq_monitor.check_quality = MagicMock(return_value=[])
        mock_dq_monitor.update_baseline_from_metrics = MagicMock()

        service = DataQualityService(
            dq_monitor=mock_dq_monitor,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
        }

        result = await service.evaluate(metrics)

        assert result.check_duration_ms >= 0
        mock_metrics.observe_histogram.assert_called_once()
        call_args = mock_metrics.observe_histogram.call_args
        assert call_args[0][0] == "dq_check_duration_ms"


@pytest.mark.unit
class TestDataQualityServiceBaselineUpdates:
    """Tests for baseline update logic."""

    @pytest.mark.asyncio
    async def test_baseline_updated_counter_incremented(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test that baseline update counter is incremented for each metric."""
        mock_dq_monitor = MagicMock()
        mock_dq_monitor.check_quality = MagicMock(return_value=[])
        mock_dq_monitor.update_baseline_from_metrics = MagicMock()

        service = DataQualityService(
            dq_monitor=mock_dq_monitor,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
            "silver_yield": 0.95,
        }

        await service.evaluate(metrics)

        # Should be called 3 times, once per metric
        baseline_calls = [
            call
            for call in mock_metrics.increment_counter.call_args_list
            if call[0][0] == "dq_baseline_updated"
        ]
        assert len(baseline_calls) == 3

    @pytest.mark.asyncio
    async def test_baseline_not_updated_on_critical_anomaly(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test that baseline is not updated when critical anomaly detected."""
        from bioetl.infrastructure.observability.anomaly.types import (
            Anomaly,
            AnomalySeverity,
            AnomalyType,
        )

        critical_anomaly = Anomaly(
            metric_name="error_rate",
            current_value=0.50,
            baseline_mean=0.05,
            baseline_stddev=0.02,
            anomaly_type=AnomalyType.THRESHOLD_EXCEEDED,
            severity=AnomalySeverity.CRITICAL,
            z_score=22.5,
            timestamp=datetime.now(UTC),
            message="Error rate critical",
        )

        mock_dq_monitor = MagicMock()
        mock_dq_monitor.check_quality = MagicMock(return_value=[critical_anomaly])
        mock_dq_monitor.update_baseline_from_metrics = MagicMock()

        service = DataQualityService(
            dq_monitor=mock_dq_monitor,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
        }

        await service.evaluate(metrics)

        # dq_baseline_updated should NOT be called
        baseline_calls = [
            call
            for call in mock_metrics.increment_counter.call_args_list
            if call[0][0] == "dq_baseline_updated"
        ]
        assert len(baseline_calls) == 0


@pytest.mark.unit
class TestDQResult:
    """Tests for DQResult dataclass."""

    def test_dq_result_creation(self):
        """Test DQResult creation with all fields."""
        result = DQResult(
            error_rate=0.05,
            status=DQStatus.WARNING,
            anomalies=(),
            has_critical=False,
            check_duration_ms=123.45,
        )

        assert result.error_rate == 0.05
        assert result.status == DQStatus.WARNING
        assert result.anomalies == ()
        assert result.has_critical is False
        assert result.check_duration_ms == 123.45

    def test_dq_result_list_to_tuple_conversion(self):
        """Test that DQResult converts list anomalies to tuple."""
        result = DQResult(
            error_rate=0.05,
            status=DQStatus.PASSED,
            anomalies=["anomaly1", "anomaly2"],  # type: ignore
        )

        assert isinstance(result.anomalies, tuple)
        assert result.anomalies == ("anomaly1", "anomaly2")

    def test_dq_result_properties(self):
        """Test DQResult property methods."""
        passed = DQResult(error_rate=0.01, status=DQStatus.PASSED)
        warning = DQResult(error_rate=0.10, status=DQStatus.WARNING)
        failed = DQResult(error_rate=0.25, status=DQStatus.FAILED)

        assert passed.is_passed is True
        assert passed.is_warning is False
        assert passed.is_failed is False

        assert warning.is_passed is False
        assert warning.is_warning is True
        assert warning.is_failed is False

        assert failed.is_passed is False
        assert failed.is_warning is False
        assert failed.is_failed is True

    def test_dq_result_anomalies_count(self):
        """Test anomalies_count property."""
        result = DQResult(
            error_rate=0.05,
            status=DQStatus.PASSED,
            anomalies=("a", "b", "c"),
        )

        assert result.anomalies_count == 3


@pytest.mark.unit
class TestDQStatus:
    """Tests for DQStatus enum."""

    def test_status_values(self):
        """Test DQStatus enum values."""
        assert DQStatus.PASSED.value == "passed"
        assert DQStatus.WARNING.value == "warning"
        assert DQStatus.FAILED.value == "failed"

    def test_status_is_string(self):
        """Test that DQStatus is a string enum."""
        assert isinstance(DQStatus.PASSED, str)
        assert DQStatus.PASSED == "passed"
