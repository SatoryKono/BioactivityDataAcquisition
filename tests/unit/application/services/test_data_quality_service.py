"""Unit tests for the DataQualityService class."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock, call

import pytest

from bioetl.application.services.data_quality_service import DataQualityService
from bioetl.domain.config import DQConfig
from bioetl.domain.exceptions.data_quality import DataQualityThresholdError
from bioetl.domain.value_objects.dq_anomaly import (
    DQAnomaly,
    DQAnomalySeverity,
    DQAnomalyType,
)
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult


def _sample_anomaly(metric_name: str = "error_rate") -> DQAnomaly:
    return DQAnomaly(
        metric_name=metric_name,
        current_value=0.2,
        baseline_mean=0.05,
        baseline_stddev=0.01,
        anomaly_type=DQAnomalyType.THRESHOLD_EXCEEDED,
        severity=DQAnomalySeverity.HIGH,
        z_score=15.0,
        timestamp=datetime.now(UTC),
        message=f"{metric_name} exceeded expected range",
    )


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
        entity_type="test_entity",
    )


@pytest.mark.unit
class TestDataQualityServiceInit:
    """Tests for DataQualityService initialization."""

    def test_initialization_without_monitor(self, mock_logger, mock_metrics, dq_config):
        """Test service initializes correctly without dq_monitor."""
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
            entity_type="test_entity",
        )

        assert service._dq_monitor is None
        assert service._config == dq_config
        assert service._logger == mock_logger
        assert service._metrics == mock_metrics
        assert service._pipeline_name == "test_pipeline"

    def test_initialization_with_monitor(self, mock_logger, mock_metrics, dq_config):
        """Test service initializes correctly with dq_monitor."""
        mock_dq_monitor = MagicMock()

        service = DataQualityService(
            dq_monitor=mock_dq_monitor,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
            entity_type="test_entity",
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
        await asyncio.sleep(0)
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
            entity_type="test_entity",
        )

        # Metrics with 25% error rate (above hard threshold of 20%)
        metrics = {
            "record_count": 100.0,
            "error_rate": 0.25,
        }

        with pytest.raises(DataQualityThresholdError) as exc_info:
            service.evaluate(metrics)

        assert exc_info.value.error_rate == pytest.approx(0.25)
        assert exc_info.value.threshold == pytest.approx(0.20)
        mock_logger.error.assert_called_once()
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_dq_validation_failures_total",
            1,
            {
                "pipeline": "test_pipeline",
                "stage": "threshold",
                "severity": "hard_fail",
            },
        )
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_dq_dispositions_total",
            1,
            {
                "pipeline": "test_pipeline",
                "stage": "validation",
                "disposition": "fail",
                "terminal_status": "failed",
            },
        )

    @pytest.mark.asyncio
    async def test_hard_threshold_exactly_at_limit_raises_error(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test that error rate exactly at hard threshold raises DataQualityThresholdError."""
        await asyncio.sleep(0)
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
            entity_type="test_entity",
        )

        # Metrics with exactly 20% error rate
        metrics = {
            "record_count": 100.0,
            "error_rate": 0.20,
        }

        with pytest.raises(DataQualityThresholdError):
            service.evaluate(metrics)

        mock_metrics.increment_counter.assert_any_call(
            "bioetl_dq_validation_failures_total",
            1,
            {
                "pipeline": "test_pipeline",
                "stage": "threshold",
                "severity": "hard_fail",
            },
        )

    @pytest.mark.asyncio
    async def test_soft_threshold_exceeded_logs_warning_and_emits_metric(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test that error rate exceeding soft threshold logs warning and emits metric."""
        await asyncio.sleep(0)
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
            entity_type="test_entity",
        )

        # Metrics with 10% error rate (above soft 5%, below hard 20%)
        metrics = {
            "record_count": 100.0,
            "error_rate": 0.10,
            "freshness_anchor_timestamp": 1_700_000_000.0,
        }

        result = service.evaluate(metrics)

        assert result.status == DQEvaluationStatus.WARNING
        assert result.error_rate == pytest.approx(0.10)
        mock_metrics.set_gauge.assert_any_call(
            "bioetl_dq_monitor_enabled",
            0.0,
            {"pipeline": "test_pipeline", "entity": "test_entity"},
        )
        warning_events = [call.args[0] for call in mock_logger.warning.call_args_list]
        assert "DQ soft threshold exceeded" in warning_events
        assert "dq_monitor_disabled" in warning_events
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_dq_soft_threshold_exceeded",
            1,
            {"pipeline": "test_pipeline"},
        )
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_dq_validation_failures_total",
            1,
            {
                "pipeline": "test_pipeline",
                "stage": "threshold",
                "severity": "soft_fail",
            },
        )
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_dq_dispositions_total",
            1,
            {
                "pipeline": "test_pipeline",
                "stage": "validation",
                "disposition": "warn",
                "terminal_status": "success",
            },
        )

    @pytest.mark.asyncio
    async def test_soft_threshold_exactly_at_limit_logs_warning(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test that error rate exactly at soft threshold logs warning."""
        await asyncio.sleep(0)
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
            entity_type="test_entity",
        )

        # Metrics with exactly 5% error rate
        metrics = {
            "record_count": 100.0,
            "error_rate": 0.05,
            "freshness_anchor_timestamp": 1_700_000_000.0,
        }

        result = service.evaluate(metrics)

        assert result.status == DQEvaluationStatus.WARNING
        warning_events = [call.args[0] for call in mock_logger.warning.call_args_list]
        assert "DQ soft threshold exceeded" in warning_events
        assert "dq_monitor_disabled" in warning_events
        soft_threshold_calls = [
            call
            for call in mock_metrics.increment_counter.call_args_list
            if call.args and call.args[0] == "bioetl_dq_soft_threshold_exceeded"
        ]
        assert len(soft_threshold_calls) == 1
        dq_failure_calls = [
            call
            for call in mock_metrics.increment_counter.call_args_list
            if call.args and call.args[0] == "bioetl_dq_validation_failures_total"
        ]
        assert len(dq_failure_calls) == 1

    @pytest.mark.asyncio
    async def test_below_soft_threshold_passes(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test that error rate below soft threshold passes without warning."""
        await asyncio.sleep(0)
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
            entity_type="test_entity",
        )

        # Metrics with 3% error rate (below soft threshold)
        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
        }

        result = service.evaluate(metrics)

        assert result.status == DQEvaluationStatus.PASSED
        assert result.error_rate == pytest.approx(0.03)
        mock_logger.warning.assert_called_once_with(
            "dq_monitor_disabled",
            pipeline="test_pipeline",
            entity="test_entity",
            reason="dq_monitor_not_configured",
        )
        mock_logger.error.assert_not_called()
        increment_counter_calls = mock_metrics.increment_counter.call_args_list
        assert call(
            "bioetl_dq_monitor_disabled_total",
            1,
            {"pipeline": "test_pipeline", "entity": "test_entity"},
        ) in increment_counter_calls
        assert call(
            "bioetl_dq_dispositions_total",
            1,
            {
                "pipeline": "test_pipeline",
                "stage": "validation",
                "disposition": "pass",
                "terminal_status": "success",
            },
        ) in increment_counter_calls


@pytest.mark.unit
class TestDataQualityServiceGracefulDegradation:
    """Tests for graceful degradation without dq_monitor."""

    @pytest.mark.asyncio
    async def test_no_monitor_returns_result_without_anomalies(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test that without dq_monitor, service returns result without anomalies."""
        await asyncio.sleep(0)
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
            entity_type="test_entity",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
        }

        result = service.evaluate(metrics)

        assert result.anomalies_count == 0
        assert result.has_critical is False
        assert result.check_duration_ms == pytest.approx(0.0)
        assert result.anomalies == ()
        mock_logger.warning.assert_called_once_with(
            "dq_monitor_disabled",
            pipeline="test_pipeline",
            entity="test_entity",
            reason="dq_monitor_not_configured",
        )
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_dq_monitor_disabled_total",
            1,
            {"pipeline": "test_pipeline", "entity": "test_entity"},
        )

    @pytest.mark.asyncio
    async def test_no_metrics_port_still_logs_warning(self, mock_logger, dq_config):
        """Test that soft threshold logs warning even when metrics port is None."""
        await asyncio.sleep(0)
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=None,  # No metrics port
            pipeline_name="test_pipeline",
            entity_type="test_entity",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.10,
        }

        result = service.evaluate(metrics)

        assert result.status == DQEvaluationStatus.WARNING
        warning_events = [call.args[0] for call in mock_logger.warning.call_args_list]
        assert "DQ soft threshold exceeded" in warning_events
        assert "dq_monitor_disabled" in warning_events


@pytest.mark.unit
class TestDataQualityServiceAnomalyDetection:
    """Tests for anomaly detection with dq_monitor."""

    @pytest.mark.asyncio
    async def test_anomaly_detection_with_no_anomalies(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test anomaly detection with no anomalies detected."""
        await asyncio.sleep(0)
        mock_dq_monitor = MagicMock()
        mock_dq_monitor.check_quality = MagicMock(return_value=[])
        mock_dq_monitor.update_baseline_from_metrics = MagicMock()

        service = DataQualityService(
            dq_monitor=mock_dq_monitor,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
            entity_type="test_entity",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
        }

        result = service.evaluate(metrics)

        assert result.anomalies_count == 0
        assert result.has_critical is False
        mock_dq_monitor.check_quality.assert_called_once_with(metrics, None)
        mock_dq_monitor.update_baseline_from_metrics.assert_called_once_with(
            metrics,
            None,
        )

    @pytest.mark.asyncio
    async def test_anomaly_detection_propagates_canonical_anchor_timestamp(
        self, mock_logger, mock_metrics, dq_config
    ) -> None:
        """DQ monitor calls should use the application-owned freshness anchor."""
        await asyncio.sleep(0)
        mock_dq_monitor = MagicMock()
        mock_dq_monitor.check_quality = MagicMock(return_value=[])
        mock_dq_monitor.update_baseline_from_metrics = MagicMock()

        service = DataQualityService(
            dq_monitor=mock_dq_monitor,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
            entity_type="test_entity",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
            "freshness_anchor_timestamp": 1_700_000_123.0,
        }

        service.evaluate(metrics)

        expected_timestamp = datetime.fromtimestamp(1_700_000_123.0, UTC)
        mock_dq_monitor.check_quality.assert_called_once_with(
            metrics,
            expected_timestamp,
        )
        mock_dq_monitor.update_baseline_from_metrics.assert_called_once_with(
            metrics,
            expected_timestamp,
        )

    @pytest.mark.asyncio
    async def test_anomaly_detection_with_anomalies(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test anomaly detection with anomalies detected."""
        await asyncio.sleep(0)
        from bioetl.infrastructure.observability.anomaly.types import (
            AnomalyRecord,
            AnomalySeverity,
            AnomalyType,
        )

        anomaly = AnomalyRecord(
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
            entity_type="test_entity",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
        }

        result = service.evaluate(metrics)

        assert result.anomalies_count == 1
        assert result.has_critical is False
        assert len(result.anomalies) == 1
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_anomaly_detection_with_critical_anomaly(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test anomaly detection with critical anomaly."""
        await asyncio.sleep(0)
        from bioetl.infrastructure.observability.anomaly.types import (
            AnomalyRecord,
            AnomalySeverity,
            AnomalyType,
        )

        critical_anomaly = AnomalyRecord(
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
            entity_type="test_entity",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
        }

        result = service.evaluate(metrics)

        assert result.anomalies_count == 1
        assert result.has_critical is True
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_check_duration_metric_emitted(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test that check duration metric is emitted."""
        await asyncio.sleep(0)
        mock_dq_monitor = MagicMock()
        mock_dq_monitor.check_quality = MagicMock(return_value=[])
        mock_dq_monitor.update_baseline_from_metrics = MagicMock()

        service = DataQualityService(
            dq_monitor=mock_dq_monitor,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
            entity_type="test_entity",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
        }

        result = service.evaluate(metrics)

        assert result.check_duration_ms >= 0
        mock_metrics.observe_histogram.assert_called_once()
        call_args = mock_metrics.observe_histogram.call_args
        assert call_args[0][0] == "bioetl_dq_check_duration_ms"


@pytest.mark.unit
class TestDataQualityServiceBaselineUpdates:
    """Tests for baseline update logic."""

    @pytest.mark.asyncio
    async def test_baseline_updated_counter_incremented(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test that baseline update counter is incremented for each metric."""
        await asyncio.sleep(0)
        mock_dq_monitor = MagicMock()
        mock_dq_monitor.check_quality = MagicMock(return_value=[])
        mock_dq_monitor.update_baseline_from_metrics = MagicMock()

        service = DataQualityService(
            dq_monitor=mock_dq_monitor,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
            entity_type="test_entity",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
            "silver_yield": 0.95,
        }

        service.evaluate(metrics)

        # Should be called 3 times, once per metric
        baseline_calls = [
            call
            for call in mock_metrics.increment_counter.call_args_list
            if call[0][0] == "bioetl_dq_baseline_updated"
        ]
        assert len(baseline_calls) == 3

    @pytest.mark.asyncio
    async def test_baseline_samples_gauge_reflects_monitor_stats(
        self, mock_logger, mock_metrics, dq_config
    ) -> None:
        await asyncio.sleep(0)
        mock_dq_monitor = MagicMock()
        mock_dq_monitor.check_quality = MagicMock(return_value=[])
        mock_dq_monitor.update_baseline_from_metrics = MagicMock()
        mock_dq_monitor.get_baseline_stats = MagicMock(
            side_effect=[
                (100.0, 5.0, 7),
                (0.03, 0.01, 4),
                (0.95, 0.02, 3),
            ]
        )

        service = DataQualityService(
            dq_monitor=mock_dq_monitor,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
            entity_type="test_entity",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
            "silver_yield": 0.95,
        }

        service.evaluate(metrics)

        baseline_sample_calls = [
            call
            for call in mock_metrics.set_gauge.call_args_list
            if call.args and call.args[0] == "bioetl_dq_baseline_samples"
        ]
        assert baseline_sample_calls == [
            call(
                "bioetl_dq_baseline_samples",
                7.0,
                {"pipeline": "test_pipeline", "metric": "record_count"},
            ),
            call(
                "bioetl_dq_baseline_samples",
                4.0,
                {"pipeline": "test_pipeline", "metric": "error_rate"},
            ),
            call(
                "bioetl_dq_baseline_samples",
                3.0,
                {"pipeline": "test_pipeline", "metric": "silver_yield"},
            ),
        ]

    @pytest.mark.asyncio
    async def test_baseline_not_updated_on_critical_anomaly(
        self, mock_logger, mock_metrics, dq_config
    ):
        """Test that baseline is not updated when critical anomaly detected."""
        await asyncio.sleep(0)
        from bioetl.infrastructure.observability.anomaly.types import (
            AnomalyRecord,
            AnomalySeverity,
            AnomalyType,
        )

        critical_anomaly = AnomalyRecord(
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
            entity_type="test_entity",
        )

        metrics = {
            "record_count": 100.0,
            "error_rate": 0.03,
        }

        service.evaluate(metrics)

        # dq_baseline_updated should NOT be called
        baseline_calls = [
            call
            for call in mock_metrics.increment_counter.call_args_list
            if call[0][0] == "bioetl_dq_baseline_updated"
        ]
        assert len(baseline_calls) == 0


@pytest.mark.unit
class TestDQResult:
    """Tests for DQResult dataclass."""

    def test_dq_result_creation(self):
        """Test DQResult creation with all fields."""
        result = DQResult(
            error_rate=0.05,
            status=DQEvaluationStatus.WARNING,
            anomalies=(),
            has_critical=False,
            check_duration_ms=123.45,
        )

        assert result.error_rate == pytest.approx(0.05)
        assert result.status == DQEvaluationStatus.WARNING
        assert result.anomalies == ()
        assert result.has_critical is False
        assert result.check_duration_ms == pytest.approx(123.45)


@pytest.mark.unit
class TestDataQualityServiceFreshnessGauge:
    """Tests for anchor-derived freshness gauge publication."""

    def test_emits_freshness_gauge_from_anchor(
        self, mock_logger, mock_metrics, dq_config
    ) -> None:
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
            entity_type="test_entity",
        )

        service.evaluate(
            {
                "record_count": 10.0,
                "error_rate": 0.0,
                "freshness_anchor_timestamp": 1_700_000_123.0,
            }
        )

        mock_metrics.set_gauge.assert_any_call(
            "bioetl_data_freshness_seconds",
            1_700_000_123.0,
            {"pipeline": "test_pipeline", "entity": "test_entity"},
        )

    def test_skips_freshness_gauge_without_anchor(
        self, mock_logger, mock_metrics, dq_config
    ) -> None:
        service = DataQualityService(
            dq_monitor=None,
            config=dq_config,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name="test_pipeline",
            entity_type="test_entity",
        )

        service.evaluate({"record_count": 10.0, "error_rate": 0.0})

        freshness_calls = [
            call
            for call in mock_metrics.set_gauge.call_args_list
            if call.args and call.args[0] == "bioetl_data_freshness_seconds"
        ]
        assert not freshness_calls

    def test_dq_result_list_to_tuple_conversion(self):
        """Test that DQResult converts list anomalies to tuple."""
        result = DQResult(
            error_rate=0.05,
            status=DQEvaluationStatus.PASSED,
            anomalies=[_sample_anomaly("error_rate"), _sample_anomaly("gold_yield")],  # type: ignore[arg-type]
        )

        assert isinstance(result.anomalies, tuple)
        assert [anomaly.metric_name for anomaly in result.anomalies] == [
            "error_rate",
            "gold_yield",
        ]

    def test_dq_result_properties(self):
        """Test DQResult property methods."""
        passed = DQResult(error_rate=0.01, status=DQEvaluationStatus.PASSED)
        warning = DQResult(error_rate=0.10, status=DQEvaluationStatus.WARNING)
        failed = DQResult(error_rate=0.25, status=DQEvaluationStatus.FAILED)

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
            status=DQEvaluationStatus.PASSED,
            anomalies=(
                _sample_anomaly("error_rate"),
                _sample_anomaly("gold_yield"),
                _sample_anomaly("record_count"),
            ),
        )

        assert result.anomalies_count == 3


@pytest.mark.unit
class TestDQEvaluationStatus:
    """Tests for DQEvaluationStatus enum."""

    def test_status_values(self):
        """Test DQEvaluationStatus enum values."""
        assert DQEvaluationStatus.PASSED.value == "passed"
        assert DQEvaluationStatus.WARNING.value == "warning"
        assert DQEvaluationStatus.FAILED.value == "failed"

    def test_status_is_string(self):
        """Test that DQEvaluationStatus is a string enum."""
        assert isinstance(DQEvaluationStatus.PASSED, str)
        assert DQEvaluationStatus.PASSED == "passed"
