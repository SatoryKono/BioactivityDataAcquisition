"""Unit tests for DQResult and DQEvaluationStatus value objects."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.value_objects.dq_anomaly import (
    DQAnomaly,
    DQAnomalySeverity,
    DQAnomalyType,
)
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult
from tests.helpers.clock import FIXED_TEST_TIME


def _sample_anomaly(metric_name: str = "error_rate") -> DQAnomaly:
    return DQAnomaly(
        metric_name=metric_name,
        current_value=0.2,
        baseline_mean=0.05,
        baseline_stddev=0.01,
        anomaly_type=DQAnomalyType.THRESHOLD_EXCEEDED,
        severity=DQAnomalySeverity.HIGH,
        z_score=15.0,
        timestamp=FIXED_TEST_TIME,
        message=f"{metric_name} exceeded expected range",
    )


@pytest.mark.unit
class TestDQEvaluationStatus:
    """Tests for DQEvaluationStatus enum."""

    def test_passed_value(self) -> None:
        """Test PASSED has correct string value."""
        assert DQEvaluationStatus.PASSED == "passed"

    def test_warning_value(self) -> None:
        """Test WARNING has correct string value."""
        assert DQEvaluationStatus.WARNING == "warning"

    def test_failed_value(self) -> None:
        """Test FAILED has correct string value."""
        assert DQEvaluationStatus.FAILED == "failed"

    def test_str_comparison(self) -> None:
        """Test StrEnum allows direct string comparison."""
        assert DQEvaluationStatus.PASSED == "passed"
        assert DQEvaluationStatus.WARNING != "passed"


@pytest.mark.unit
class TestDQResult:
    """Tests for DQResult value object."""

    def test_minimal_creation(self) -> None:
        """Test creating DQResult with required fields."""
        result = DQResult(
            error_rate=0.01,
            status=DQEvaluationStatus.PASSED,
        )
        assert result.error_rate == pytest.approx(0.01)
        assert result.status == DQEvaluationStatus.PASSED
        assert result.anomalies == ()
        assert result.has_critical is False
        assert result.check_duration_ms == pytest.approx(0.0)

    def test_full_creation(self) -> None:
        """Test creating DQResult with all fields."""
        result = DQResult(
            error_rate=0.10,
            status=DQEvaluationStatus.WARNING,
            anomalies=(_sample_anomaly("error_rate"), _sample_anomaly("silver_yield")),
            has_critical=False,
            check_duration_ms=45.7,
        )
        assert result.anomalies[0].metric_name == "error_rate"
        assert result.anomalies[1].metric_name == "silver_yield"
        assert result.check_duration_ms == pytest.approx(45.7)

    def test_list_anomalies_converted_to_tuple(self) -> None:
        """Test that list anomalies are converted to tuple (immutability)."""
        result = DQResult(
            error_rate=0.05,
            status=DQEvaluationStatus.WARNING,
            anomalies=[_sample_anomaly("error_rate"), _sample_anomaly("silver_yield")],  # type: ignore[arg-type]
        )
        assert isinstance(result.anomalies, tuple)
        assert [anomaly.metric_name for anomaly in result.anomalies] == [
            "error_rate",
            "silver_yield",
        ]

    def test_is_passed_when_passed(self) -> None:
        """Test is_passed returns True for PASSED status."""
        result = DQResult(
            error_rate=0.01,
            status=DQEvaluationStatus.PASSED,
        )
        assert result.is_passed is True
        assert result.is_warning is False
        assert result.is_failed is False

    def test_is_warning_when_warning(self) -> None:
        """Test is_warning returns True for WARNING status."""
        result = DQResult(
            error_rate=0.08,
            status=DQEvaluationStatus.WARNING,
        )
        assert result.is_passed is False
        assert result.is_warning is True
        assert result.is_failed is False

    def test_is_failed_when_failed(self) -> None:
        """Test is_failed returns True for FAILED status."""
        result = DQResult(
            error_rate=0.25,
            status=DQEvaluationStatus.FAILED,
            has_critical=True,
        )
        assert result.is_passed is False
        assert result.is_warning is False
        assert result.is_failed is True
        assert result.has_critical is True

    def test_anomalies_count(self) -> None:
        """Test anomalies_count returns correct count."""
        result = DQResult(
            error_rate=0.10,
            status=DQEvaluationStatus.WARNING,
            anomalies=(
                _sample_anomaly("error_rate"),
                _sample_anomaly("silver_yield"),
                _sample_anomaly("gold_yield"),
            ),
        )
        assert result.anomalies_count == 3

    def test_anomalies_count_empty(self) -> None:
        """Test anomalies_count returns 0 for empty anomalies."""
        result = DQResult(
            error_rate=0.0,
            status=DQEvaluationStatus.PASSED,
        )
        assert result.anomalies_count == 0

    def test_is_frozen(self) -> None:
        """Test DQResult is immutable (frozen dataclass)."""
        result = DQResult(
            error_rate=0.01,
            status=DQEvaluationStatus.PASSED,
        )
        with pytest.raises((AttributeError, TypeError)):
            result.error_rate = 0.99  # type: ignore[misc]
