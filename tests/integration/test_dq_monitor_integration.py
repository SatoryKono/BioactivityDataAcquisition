"""Integration tests for Data Quality Monitor.

Tests the full DQ monitor flow including anomaly detection,
baseline updates, and threshold violations.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from bioetl.domain.value_objects.dq_anomaly import (
    DQAnomaly,
    DQAnomalySeverity,
    DQAnomalyType,
)
from bioetl.infrastructure.observability.anomaly import DataQualityMonitorService


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger for tests."""
    return MagicMock()


@pytest.mark.integration
class TestDQMonitorAnomalyDetection:
    """Integration tests for anomaly detection."""

    def test_dq_monitor_detects_spike(self, mock_logger: MagicMock) -> None:
        """DQ Monitor should detect record count spike."""
        monitor = DataQualityMonitorService(logger=mock_logger, z_score_threshold=2.0)

        # Build baseline with normal values
        for _ in range(5):
            monitor.update_baseline_from_metrics({"record_count": 1000.0})

        # Check with spike
        anomalies = monitor.check_quality(
            {"record_count": 5000.0}, timestamp=datetime.now(UTC)
        )

        assert len(anomalies) == 1
        assert isinstance(anomalies[0], DQAnomaly)
        assert anomalies[0].anomaly_type == DQAnomalyType.SPIKE
        assert anomalies[0].severity in (
            DQAnomalySeverity.HIGH,
            DQAnomalySeverity.CRITICAL,
        )

    def test_dq_monitor_detects_drop(self, mock_logger: MagicMock) -> None:
        """DQ Monitor should detect record count drop."""
        monitor = DataQualityMonitorService(logger=mock_logger, z_score_threshold=2.0)

        # Build baseline with slight variation (required for stddev > 0)
        for value in [980.0, 1000.0, 1020.0, 990.0, 1010.0]:
            monitor.update_baseline_from_metrics({"record_count": value})

        # Check with significant drop (z-score will be high)
        anomalies = monitor.check_quality(
            {"record_count": 100.0}, timestamp=datetime.now(UTC)
        )

        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == DQAnomalyType.DROP

    def test_dq_monitor_threshold_exceeded(self, mock_logger: MagicMock) -> None:
        """DQ Monitor should detect threshold violations."""
        monitor = DataQualityMonitorService(logger=mock_logger)
        monitor.detector.set_threshold("error_rate", min_value=0.0, max_value=0.10)

        anomalies = monitor.check_quality(
            {"error_rate": 0.25}, timestamp=datetime.now(UTC)
        )

        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == DQAnomalyType.THRESHOLD_EXCEEDED
        assert anomalies[0].severity == DQAnomalySeverity.CRITICAL

    def test_dq_monitor_no_anomalies_within_range(self, mock_logger: MagicMock) -> None:
        """DQ Monitor should not detect anomalies for normal values."""
        monitor = DataQualityMonitorService(logger=mock_logger, z_score_threshold=2.0)

        # Build baseline
        for _ in range(5):
            monitor.update_baseline_from_metrics({"record_count": 1000.0})

        # Check with value close to baseline
        anomalies = monitor.check_quality(
            {"record_count": 1050.0}, timestamp=datetime.now(UTC)
        )

        assert len(anomalies) == 0

    def test_dq_monitor_updates_baseline(self, mock_logger: MagicMock) -> None:
        """DQ Monitor should update baseline with new metrics."""
        monitor = DataQualityMonitorService(logger=mock_logger)

        # Initial update
        monitor.update_baseline_from_metrics({"record_count": 1000.0})
        stats = monitor.get_baseline_stats("record_count")

        assert stats is not None
        mean, _stddev, count = stats
        assert count == 1
        assert mean == pytest.approx(1000.0)

        # Second update
        monitor.update_baseline_from_metrics({"record_count": 2000.0})
        stats = monitor.get_baseline_stats("record_count")

        assert stats is not None
        mean, _stddev, count = stats
        assert count == 2
        assert mean == pytest.approx(1500.0)  # Average of 1000 and 2000


@pytest.mark.integration
class TestDQMonitorSeverityLevels:
    """Tests for severity level determination."""

    def test_low_severity_for_small_deviation(self, mock_logger: MagicMock) -> None:
        """Small deviations should get LOW severity."""
        monitor = DataQualityMonitorService(logger=mock_logger, z_score_threshold=2.0)

        # Build baseline with consistent values
        # mean=100, stddev≈1.58
        for value in [100.0, 102.0, 98.0, 101.0, 99.0]:
            monitor.detector.add_baseline_value("metric", value)

        # Value that gives z-score ~2.5 (between 2.0 and 3.0 for LOW severity)
        # z = |104 - 100| / 1.58 ≈ 2.53
        anomalies = monitor.check_quality(
            {"metric": 104.0}, timestamp=datetime.now(UTC)
        )

        assert len(anomalies) == 1
        assert anomalies[0].severity == DQAnomalySeverity.LOW

    def test_critical_severity_for_extreme_deviation(
        self, mock_logger: MagicMock
    ) -> None:
        """Extreme deviations should get CRITICAL severity."""
        monitor = DataQualityMonitorService(logger=mock_logger, z_score_threshold=2.0)

        # Build baseline with consistent values
        for value in [100.0, 102.0, 98.0, 101.0, 99.0]:
            monitor.detector.add_baseline_value("metric", value)

        # Extreme value (z-score > 5)
        anomalies = monitor.check_quality(
            {"metric": 200.0}, timestamp=datetime.now(UTC)
        )

        assert len(anomalies) == 1
        assert anomalies[0].severity == DQAnomalySeverity.CRITICAL


@pytest.mark.integration
class TestDQMonitorBaselineManagement:
    """Tests for baseline management behavior."""

    def test_baseline_not_updated_on_critical_anomaly(
        self, mock_logger: MagicMock
    ) -> None:
        """Baseline should not be updated when critical anomaly detected."""
        monitor = DataQualityMonitorService(logger=mock_logger, z_score_threshold=2.0)
        monitor.detector.set_threshold("error_rate", min_value=0.0, max_value=0.10)

        # Add initial baseline
        monitor.detector.add_baseline_value("error_rate", 0.05)
        monitor.detector.add_baseline_value("error_rate", 0.04)
        monitor.detector.add_baseline_value("error_rate", 0.06)

        initial_stats = monitor.get_baseline_stats("error_rate")
        initial_count = initial_stats[2] if initial_stats else 0

        # Update with critical violation
        monitor.update_baseline_from_metrics(
            {"error_rate": 0.50}, timestamp=datetime.now(UTC)
        )

        # Baseline should not be updated
        final_stats = monitor.get_baseline_stats("error_rate")
        final_count = final_stats[2] if final_stats else 0

        assert final_count == initial_count

    def test_baseline_window_limits_samples(self, mock_logger: MagicMock) -> None:
        """Baseline should respect window size limit."""
        monitor = DataQualityMonitorService(logger=mock_logger, baseline_window=5)

        # Add more samples than window size
        for i in range(10):
            monitor.detector.add_baseline_value("metric", float(i * 100))

        stats = monitor.get_baseline_stats("metric")
        assert stats is not None
        _, _, count = stats
        assert count == 5  # Only last 5 values kept


# =============================================================================
# Integration tests for DataQualityService metrics emission (ISSUE-002)
# =============================================================================


class RecordingMetrics:
    """Test implementation of MetricsPort that records all metrics calls.

    Captures metric emissions for verification in integration tests.
    Implements MetricsPort protocol.
    """

    def __init__(self) -> None:
        """Initialize with empty records."""
        self.counters: list[tuple[str, int, dict[str, str]]] = []
        self.histograms: list[tuple[str, float, dict[str, str]]] = []
        self.gauges: list[tuple[str, float, dict[str, str]]] = []

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: dict[str, str],
    ) -> None:
        """Record counter increment."""
        self.counters.append((name, value, labels))

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        """Record histogram observation."""
        self.histograms.append((name, value, labels))

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        """Record gauge set."""
        self.gauges.append((name, value, labels))

    def close(self) -> None:
        """No-op close."""
        pass

    def get_counter_calls(self, name: str) -> list[tuple[str, int, dict[str, str]]]:
        """Get all calls to a specific counter."""
        return [c for c in self.counters if c[0] == name]

    def get_histogram_calls(self, name: str) -> list[tuple[str, float, dict[str, str]]]:
        """Get all calls to a specific histogram."""
        return [h for h in self.histograms if h[0] == name]

    def get_gauge_calls(self, name: str) -> list[tuple[str, float, dict[str, str]]]:
        """Get all calls to a specific gauge."""
        return [g for g in self.gauges if g[0] == name]


class RecordingLogger:
    """Test implementation of LoggerPort that records all log calls."""

    def __init__(self) -> None:
        """Initialize with empty records."""
        self.logs: list[tuple[str, str, dict]] = []  # (level, event, kwargs)

    def bind(self, **kwargs):  # type: ignore
        """Return self for chaining."""
        return self

    def info(self, _event: str, **kwargs) -> None:  # type: ignore
        """Record info log."""
        self.logs.append(("info", _event, kwargs))

    def warning(self, _event: str, **kwargs) -> None:  # type: ignore
        """Record warning log."""
        self.logs.append(("warning", _event, kwargs))

    def error(self, _event: str, **kwargs) -> None:  # type: ignore
        """Record error log."""
        self.logs.append(("error", _event, kwargs))

    def debug(self, _event: str, **kwargs) -> None:  # type: ignore
        """Record debug log."""
        self.logs.append(("debug", _event, kwargs))

    def exception(self, _event: str, **kwargs) -> None:  # type: ignore
        """Record exception log."""
        self.logs.append(("exception", _event, kwargs))


@pytest.mark.integration
class TestDataQualityServiceMetricsEmission:
    """Integration tests for DataQualityService metrics emission.

    These tests verify that DQ metrics are correctly emitted through
    a real (recording) MetricsPort implementation, not mocks.

    Validates ISSUE-002: DQ metrics emission verification.
    """

    @pytest.fixture
    def recording_metrics(self) -> RecordingMetrics:
        """Create a recording metrics implementation."""
        return RecordingMetrics()

    @pytest.fixture
    def recording_logger(self) -> RecordingLogger:
        """Create a recording logger implementation."""
        return RecordingLogger()

    @pytest.mark.asyncio
    async def test_soft_threshold_exceeded_emits_counter(
        self,
        recording_metrics: RecordingMetrics,
        recording_logger: RecordingLogger,
    ) -> None:
        """Verify bioetl_dq_soft_threshold_exceeded counter is emitted.

        When error_rate exceeds soft threshold (5%) but below hard (20%),
        the service MUST emit the bioetl_dq_soft_threshold_exceeded counter.
        """
        await asyncio.sleep(0)
        from bioetl.application.services.data_quality_service import DataQualityService
        from bioetl.domain.config import DQConfig
        from bioetl.domain.value_objects.dq_result import DQEvaluationStatus

        config = DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20)
        service = DataQualityService(
            dq_monitor=None,
            config=config,
            logger=recording_logger,  # type: ignore
            metrics=recording_metrics,
            pipeline_name="test_integration_pipeline",
            entity_type="test_entity",
        )

        # Error rate 10% - above soft (5%), below hard (20%)
        result = service.evaluate({"error_rate": 0.10})

        assert result.status == DQEvaluationStatus.WARNING

        # Verify counter was emitted
        counter_calls = recording_metrics.get_counter_calls(
            "bioetl_dq_soft_threshold_exceeded"
        )
        assert len(counter_calls) == 1
        name, value, labels = counter_calls[0]
        assert name == "bioetl_dq_soft_threshold_exceeded"
        assert value == 1
        assert labels == {"pipeline": "test_integration_pipeline"}

    @pytest.mark.asyncio
    async def test_check_duration_histogram_emitted_with_monitor(
        self,
        recording_metrics: RecordingMetrics,
        recording_logger: RecordingLogger,
    ) -> None:
        """Verify bioetl_dq_check_duration_ms histogram is emitted.

        When DQ monitor is present and runs anomaly detection,
        the service MUST emit check duration histogram.
        """
        await asyncio.sleep(0)
        from bioetl.application.services.data_quality_service import DataQualityService
        from bioetl.domain.config import DQConfig
        from bioetl.infrastructure.observability.anomaly import (
            DataQualityMonitorService,
        )

        config = DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20)
        dq_monitor = DataQualityMonitorService(logger=recording_logger)  # type: ignore

        service = DataQualityService(
            dq_monitor=dq_monitor,
            config=config,
            logger=recording_logger,  # type: ignore
            metrics=recording_metrics,
            pipeline_name="test_integration_pipeline",
            entity_type="test_entity",
        )

        # Normal metrics - below all thresholds
        result = service.evaluate({"error_rate": 0.01, "record_count": 100.0})

        # Verify histogram was emitted
        histogram_calls = recording_metrics.get_histogram_calls(
            "bioetl_dq_check_duration_ms"
        )
        assert len(histogram_calls) == 1
        name, value, labels = histogram_calls[0]
        assert name == "bioetl_dq_check_duration_ms"
        assert value >= 0  # Duration should be non-negative
        assert labels == {"pipeline": "test_integration_pipeline"}

        # Also verify the result has duration
        assert result.check_duration_ms >= 0

    @pytest.mark.asyncio
    async def test_validation_score_emits_volume_aware_gauges(
        self,
        recording_metrics: RecordingMetrics,
        recording_logger: RecordingLogger,
    ) -> None:
        """DQ service should emit score and the matching record-count gauge."""
        await asyncio.sleep(0)
        from bioetl.application.services.data_quality_service import DataQualityService
        from bioetl.domain.config import DQConfig

        config = DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20)
        service = DataQualityService(
            dq_monitor=None,
            config=config,
            logger=recording_logger,  # type: ignore
            metrics=recording_metrics,
            pipeline_name="test_integration_pipeline",
            entity_type="test_entity",
        )

        service.evaluate(
            {
                "error_rate": 0.02,
                "record_count": 250.0,
                "freshness_anchor_timestamp": 1_700_000_123.0,
            }
        )

        score_calls = recording_metrics.get_gauge_calls("bioetl_dq_validation_score")
        count_calls = recording_metrics.get_gauge_calls(
            "bioetl_dq_validation_record_count"
        )
        freshness_calls = recording_metrics.get_gauge_calls(
            "bioetl_data_freshness_seconds"
        )

        assert score_calls == [
            (
                "bioetl_dq_validation_score",
                0.98,
                {"pipeline": "test_integration_pipeline", "entity": "test_entity"},
            )
        ]
        assert count_calls == [
            (
                "bioetl_dq_validation_record_count",
                250.0,
                {"pipeline": "test_integration_pipeline", "entity": "test_entity"},
            )
        ]
        assert freshness_calls == [
            (
                "bioetl_data_freshness_seconds",
                1_700_000_123.0,
                {"pipeline": "test_integration_pipeline", "entity": "test_entity"},
            )
        ]

    @pytest.mark.asyncio
    async def test_dq_service_performs_check_with_monitor(
        self,
        recording_metrics: RecordingMetrics,
        recording_logger: RecordingLogger,
    ) -> None:
        """Verify DataQualityService performs DQ check with monitor.

        This test verifies:
        1. The check_quality call is made (duration > 0)
        2. Histogram for check duration is emitted
        3. Baseline is updated
        """
        await asyncio.sleep(0)
        from bioetl.application.services.data_quality_service import DataQualityService
        from bioetl.domain.config import DQConfig
        from bioetl.infrastructure.observability.anomaly import (
            DataQualityMonitorService,
        )

        config = DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20)
        dq_monitor = DataQualityMonitorService(
            logger=recording_logger, z_score_threshold=2.0
        )  # type: ignore

        service = DataQualityService(
            dq_monitor=dq_monitor,
            config=config,
            logger=recording_logger,  # type: ignore
            metrics=recording_metrics,
            pipeline_name="test_integration_pipeline",
            entity_type="test_entity",
        )

        # Evaluate with normal metrics
        result = service.evaluate({"error_rate": 0.01, "record_count": 1000.0})

        # Verify check was performed
        assert result.check_duration_ms >= 0

        # Verify histogram was emitted for check duration
        histogram_calls = recording_metrics.get_histogram_calls(
            "bioetl_dq_check_duration_ms"
        )
        assert len(histogram_calls) == 1

        # Verify baseline update counter was emitted
        baseline_calls = recording_metrics.get_counter_calls(
            "bioetl_dq_baseline_updated"
        )
        assert len(baseline_calls) == 2  # error_rate and record_count

    @pytest.mark.asyncio
    async def test_dq_service_uses_anchor_for_deterministic_anomaly_timing(
        self,
        recording_metrics: RecordingMetrics,
        recording_logger: RecordingLogger,
    ) -> None:
        """Freshness anchor should drive anomaly timestamps and detection."""
        await asyncio.sleep(0)
        from bioetl.application.services.data_quality_service import DataQualityService
        from bioetl.domain.config import DQConfig
        from bioetl.domain.value_objects.dq_anomaly import DQAnomalyType
        from bioetl.infrastructure.observability.anomaly import (
            DataQualityMonitorService,
        )

        config = DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20)
        dq_monitor = DataQualityMonitorService(
            logger=recording_logger, z_score_threshold=2.0
        )  # type: ignore
        for value in [980.0, 1000.0, 1020.0, 990.0, 1010.0]:
            dq_monitor.update_baseline_from_metrics({"record_count": value})

        service = DataQualityService(
            dq_monitor=dq_monitor,
            config=config,
            logger=recording_logger,  # type: ignore
            metrics=recording_metrics,
            pipeline_name="test_integration_pipeline",
            entity_type="test_entity",
        )

        result = service.evaluate(
            {
                "error_rate": 0.01,
                "record_count": 100.0,
                "freshness_anchor_timestamp": 1_700_000_123.0,
            }
        )

        assert result.anomalies_count == 1
        assert result.anomalies[0].anomaly_type == DQAnomalyType.DROP
        assert result.anomalies[0].timestamp == datetime.fromtimestamp(
            1_700_000_123.0, UTC
        )

    @pytest.mark.asyncio
    async def test_baseline_updated_counter_emitted(
        self,
        recording_metrics: RecordingMetrics,
        recording_logger: RecordingLogger,
    ) -> None:
        """Verify bioetl_dq_baseline_updated counter is emitted.

        When baseline is updated after successful DQ check,
        the service MUST emit baseline update counter for each metric.
        """
        await asyncio.sleep(0)
        from bioetl.application.services.data_quality_service import DataQualityService
        from bioetl.domain.config import DQConfig
        from bioetl.infrastructure.observability.anomaly import (
            DataQualityMonitorService,
        )

        config = DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20)
        dq_monitor = DataQualityMonitorService(logger=recording_logger)  # type: ignore

        service = DataQualityService(
            dq_monitor=dq_monitor,
            config=config,
            logger=recording_logger,  # type: ignore
            metrics=recording_metrics,
            pipeline_name="test_integration_pipeline",
            entity_type="test_entity",
        )

        # Evaluate with multiple metrics
        service.evaluate(
            {
                "error_rate": 0.01,
                "record_count": 100.0,
                "silver_yield": 0.95,
            }
        )

        # Verify baseline_updated counter was emitted for each metric
        counter_calls = recording_metrics.get_counter_calls(
            "bioetl_dq_baseline_updated"
        )
        assert len(counter_calls) == 3  # One per metric

        # Check all have correct pipeline label
        for name, value, labels in counter_calls:
            assert name == "bioetl_dq_baseline_updated"
            assert value == 1
            assert labels["pipeline"] == "test_integration_pipeline"
            assert "metric" in labels

        # Verify all metrics are covered
        updated_metrics = {c[2]["metric"] for c in counter_calls}
        assert updated_metrics == {"error_rate", "record_count", "silver_yield"}

    @pytest.mark.asyncio
    async def test_no_metrics_emitted_below_soft_threshold(
        self,
        recording_metrics: RecordingMetrics,
        recording_logger: RecordingLogger,
    ) -> None:
        """Verify no threshold counters emitted when below soft threshold.

        When error_rate is below soft threshold (5%),
        the service MUST NOT emit bioetl_dq_soft_threshold_exceeded counter.
        """
        await asyncio.sleep(0)
        from bioetl.application.services.data_quality_service import DataQualityService
        from bioetl.domain.config import DQConfig
        from bioetl.domain.value_objects.dq_result import DQEvaluationStatus

        config = DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20)
        service = DataQualityService(
            dq_monitor=None,
            config=config,
            logger=recording_logger,  # type: ignore
            metrics=recording_metrics,
            pipeline_name="test_integration_pipeline",
            entity_type="test_entity",
        )

        # Error rate 3% - below soft threshold
        result = service.evaluate({"error_rate": 0.03})

        assert result.status == DQEvaluationStatus.PASSED

        # Verify NO counter was emitted
        counter_calls = recording_metrics.get_counter_calls(
            "bioetl_dq_soft_threshold_exceeded"
        )
        assert len(counter_calls) == 0

    @pytest.mark.asyncio
    async def test_full_dq_flow_metrics_integration(
        self,
        recording_metrics: RecordingMetrics,
        recording_logger: RecordingLogger,
    ) -> None:
        """End-to-end test of DQ metrics flow.

        Full integration test covering:
        1. Soft threshold warning with counter (via DQConfig)
        2. Check duration histogram (via DQ monitor)
        3. Baseline update counters (via DQ monitor)
        """
        await asyncio.sleep(0)
        from bioetl.application.services.data_quality_service import DataQualityService
        from bioetl.domain.config import DQConfig
        from bioetl.infrastructure.observability.anomaly import (
            DataQualityMonitorService,
        )

        config = DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20)
        dq_monitor = DataQualityMonitorService(
            logger=recording_logger, z_score_threshold=2.0
        )  # type: ignore

        service = DataQualityService(
            dq_monitor=dq_monitor,
            config=config,
            logger=recording_logger,  # type: ignore
            metrics=recording_metrics,
            pipeline_name="e2e_test_pipeline",
            entity_type="test_entity",
        )

        # Trigger soft threshold warning
        service.evaluate(
            {
                "error_rate": 0.10,  # Above soft threshold (5%)
                "record_count": 1000.0,
            }
        )

        # Verify soft threshold counter
        soft_calls = recording_metrics.get_counter_calls(
            "bioetl_dq_soft_threshold_exceeded"
        )
        assert len(soft_calls) == 1, (
            "bioetl_dq_soft_threshold_exceeded should be emitted"
        )

        # Verify check duration histogram
        duration_calls = recording_metrics.get_histogram_calls(
            "bioetl_dq_check_duration_ms"
        )
        assert len(duration_calls) == 1, "bioetl_dq_check_duration_ms should be emitted"

        # Verify baseline update counters
        baseline_calls = recording_metrics.get_counter_calls(
            "bioetl_dq_baseline_updated"
        )
        assert len(baseline_calls) == 2, (
            "bioetl_dq_baseline_updated should be emitted for each metric"
        )
