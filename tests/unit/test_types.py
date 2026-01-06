"""Tests for domain types."""

from __future__ import annotations

from bioetl.domain.types import (
    CircuitBreakerState,
    DataClassification,
    DQStatus,
    DriftLevel,
    ErrorType,
    HealthStatus,
    RunType,
)


class TestRunType:
    """Tests for RunType enum."""

    def test_run_type_values(self) -> None:
        """RunType should have correct string values."""
        assert RunType.INCREMENTAL.value == "incremental"
        assert RunType.BACKFILL.value == "backfill"
        assert RunType.REBUILD.value == "rebuild"

    def test_priority_ordering(self) -> None:
        """REBUILD > BACKFILL > INCREMENTAL in priority."""
        assert RunType.REBUILD.priority() > RunType.BACKFILL.priority()
        assert RunType.BACKFILL.priority() > RunType.INCREMENTAL.priority()

    def test_priority_values(self) -> None:
        """Priority values should be as documented."""
        assert RunType.REBUILD.priority() == 3
        assert RunType.BACKFILL.priority() == 2
        assert RunType.INCREMENTAL.priority() == 1

    def test_run_type_is_str_enum(self) -> None:
        """RunType should be usable as string via .value."""
        assert RunType.INCREMENTAL.value == "incremental"
        assert f"run_{RunType.BACKFILL.value}" == "run_backfill"


class TestDriftLevel:
    """Tests for DriftLevel enum."""

    def test_drift_level_values(self) -> None:
        """DriftLevel should have correct string values."""
        assert DriftLevel.INFO.value == "INFO"
        assert DriftLevel.WARN.value == "WARN"
        assert DriftLevel.CRITICAL.value == "CRITICAL"


class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_health_status_values(self) -> None:
        """HealthStatus should have correct string values."""
        assert HealthStatus.HEALTHY.value == "HEALTHY"
        assert HealthStatus.DEGRADED.value == "DEGRADED"
        assert HealthStatus.UNHEALTHY.value == "UNHEALTHY"

    def test_to_metric_value(self) -> None:
        """Metric values should follow HEALTHY > DEGRADED > UNHEALTHY."""
        assert HealthStatus.HEALTHY.to_metric_value() == 2
        assert HealthStatus.DEGRADED.to_metric_value() == 1
        assert HealthStatus.UNHEALTHY.to_metric_value() == 0

    def test_metric_value_ordering(self) -> None:
        """Higher metric value = healthier status."""
        assert (
            HealthStatus.HEALTHY.to_metric_value()
            > HealthStatus.DEGRADED.to_metric_value()
        )
        assert (
            HealthStatus.DEGRADED.to_metric_value()
            > HealthStatus.UNHEALTHY.to_metric_value()
        )


class TestCircuitBreakerState:
    """Tests for CircuitBreakerState enum."""

    def test_circuit_breaker_values(self) -> None:
        """CircuitBreakerState should have correct string values."""
        assert CircuitBreakerState.CLOSED.value == "CLOSED"
        assert CircuitBreakerState.OPEN.value == "OPEN"
        assert CircuitBreakerState.HALF_OPEN.value == "HALF_OPEN"

    def test_to_metric_value(self) -> None:
        """Metric values should indicate severity."""
        assert CircuitBreakerState.CLOSED.to_metric_value() == 0
        assert CircuitBreakerState.HALF_OPEN.to_metric_value() == 1
        assert CircuitBreakerState.OPEN.to_metric_value() == 2

    def test_metric_value_severity(self) -> None:
        """Higher metric value = worse state."""
        assert (
            CircuitBreakerState.OPEN.to_metric_value()
            > CircuitBreakerState.HALF_OPEN.to_metric_value()
        )
        assert (
            CircuitBreakerState.HALF_OPEN.to_metric_value()
            > CircuitBreakerState.CLOSED.to_metric_value()
        )


class TestErrorType:
    """Tests for ErrorType enum."""

    def test_critical_errors(self) -> None:
        """Critical errors should stop the pipeline."""
        critical_errors = [
            ErrorType.AUTH_FAILURE,
            ErrorType.SCHEMA_MISMATCH_GOLD,
            ErrorType.DB_UNAVAILABLE,
            ErrorType.LOCK_LOST,
        ]
        for error in critical_errors:
            assert error.is_critical() is True, f"{error} should be critical"
            assert error.is_recoverable() is False, f"{error} should not be recoverable"
            assert error.is_data_quality() is False, (
                f"{error} should not be data quality"
            )

    def test_recoverable_errors(self) -> None:
        """Recoverable errors should be retried."""
        recoverable_errors = [
            ErrorType.RATE_LIMIT,
            ErrorType.TIMEOUT,
            ErrorType.NETWORK_ERROR,
        ]
        for error in recoverable_errors:
            assert error.is_recoverable() is True, f"{error} should be recoverable"
            assert error.is_critical() is False, f"{error} should not be critical"
            assert error.is_data_quality() is False, (
                f"{error} should not be data quality"
            )

    def test_data_quality_errors(self) -> None:
        """Data quality errors should skip the record."""
        dq_errors = [
            ErrorType.SCHEMA_VIOLATION,
            ErrorType.INVALID_DATA,
            ErrorType.MISSING_REQUIRED_FIELD,
        ]
        for error in dq_errors:
            assert error.is_data_quality() is True, f"{error} should be data quality"
            assert error.is_critical() is False, f"{error} should not be critical"
            assert error.is_recoverable() is False, f"{error} should not be recoverable"

    def test_error_categories_are_mutually_exclusive(self) -> None:
        """Each error should belong to exactly one category."""
        for error in ErrorType:
            categories = [
                error.is_critical(),
                error.is_recoverable(),
                error.is_data_quality(),
            ]
            assert sum(categories) == 1, (
                f"{error} should belong to exactly one category"
            )


class TestDataClassification:
    """Tests for DataClassification enum."""

    def test_classification_values(self) -> None:
        """DataClassification should have correct values."""
        assert DataClassification.PUBLIC.value == "PUBLIC"
        assert DataClassification.INTERNAL.value == "INTERNAL"
        assert DataClassification.RESTRICTED.value == "RESTRICTED"


class TestDQStatus:
    """Tests for DQStatus enum."""

    def test_dq_status_values(self) -> None:
        """DQStatus should have correct values."""
        assert DQStatus.NEW.value == "NEW"
        assert DQStatus.IGNORED.value == "IGNORED"
        assert DQStatus.REPROCESSED.value == "REPROCESSED"
