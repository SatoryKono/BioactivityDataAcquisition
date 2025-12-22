"""Unit tests for domain types.

Tests business logic within Enum classes.
"""

import pytest

from bioetl.domain.types import CircuitBreakerState, ErrorType, HealthStatus, RunType


@pytest.mark.unit
class TestRunType:
    """Test RunType enum."""

    def test_priority(self):
        """Test priority logic for run types."""
        assert RunType.REBUILD.priority() > RunType.BACKFILL.priority()
        assert RunType.BACKFILL.priority() > RunType.INCREMENTAL.priority()
        assert RunType.REBUILD.priority() == 3
        assert RunType.BACKFILL.priority() == 2
        assert RunType.INCREMENTAL.priority() == 1


@pytest.mark.unit
class TestHealthStatus:
    """Test HealthStatus enum."""

    def test_to_metric_value(self):
        """Test conversion to Prometheus metric value."""
        assert HealthStatus.HEALTHY.to_metric_value() == 2
        assert HealthStatus.DEGRADED.to_metric_value() == 1
        assert HealthStatus.UNHEALTHY.to_metric_value() == 0


@pytest.mark.unit
class TestCircuitBreakerState:
    """Test CircuitBreakerState enum."""

    def test_to_metric_value(self):
        """Test conversion to Prometheus metric value."""
        assert CircuitBreakerState.CLOSED.to_metric_value() == 0
        assert CircuitBreakerState.HALF_OPEN.to_metric_value() == 1
        assert CircuitBreakerState.OPEN.to_metric_value() == 2


@pytest.mark.unit
class TestErrorType:
    """Test ErrorType enum classification logic."""

    def test_is_critical(self):
        """Test critical error classification."""
        assert ErrorType.AUTH_FAILURE.is_critical()
        assert ErrorType.SCHEMA_MISMATCH_GOLD.is_critical()
        assert ErrorType.DB_UNAVAILABLE.is_critical()
        assert ErrorType.LOCK_LOST.is_critical()
        # Non-critical
        assert not ErrorType.RATE_LIMIT.is_critical()
        assert not ErrorType.INVALID_DATA.is_critical()

    def test_is_recoverable(self):
        """Test recoverable error classification."""
        assert ErrorType.RATE_LIMIT.is_recoverable()
        assert ErrorType.TIMEOUT.is_recoverable()
        assert ErrorType.NETWORK_ERROR.is_recoverable()
        # Non-recoverable
        assert not ErrorType.AUTH_FAILURE.is_recoverable()
        assert not ErrorType.SCHEMA_VIOLATION.is_recoverable()

    def test_is_data_quality(self):
        """Test data quality error classification."""
        assert ErrorType.SCHEMA_VIOLATION.is_data_quality()
        assert ErrorType.INVALID_DATA.is_data_quality()
        assert ErrorType.MISSING_REQUIRED_FIELD.is_data_quality()
        # Non-data quality
        assert not ErrorType.RATE_LIMIT.is_data_quality()
        assert not ErrorType.DB_UNAVAILABLE.is_data_quality()
