"""Tests for domain enumerations.

Tests for RunType, HealthStatus, ErrorType, CircuitBreakerState, etc.
"""

from __future__ import annotations

import pytest

from bioetl.domain.types.enums import (
    CellularityType,
    CircuitBreakerState,
    DataClassification,
    DriftLevel,
    ErrorType,
    ExecutionContext,
    HealthStatus,
    PublicationType,
    QuarantineRecordStatus,
    RunType,
)


@pytest.mark.unit
class TestRunType:
    """Tests for RunType enum."""

    def test_values(self) -> None:
        assert RunType.INCREMENTAL == "incremental"
        assert RunType.BACKFILL == "backfill"
        assert RunType.REBUILD == "rebuild"

    def test_priority_ordering(self) -> None:
        assert RunType.REBUILD.priority() > RunType.BACKFILL.priority()
        assert RunType.BACKFILL.priority() > RunType.INCREMENTAL.priority()

    def test_priority_values(self) -> None:
        assert RunType.INCREMENTAL.priority() == 1
        assert RunType.BACKFILL.priority() == 2
        assert RunType.REBUILD.priority() == 3


@pytest.mark.unit
class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_values(self) -> None:
        assert HealthStatus.HEALTHY == "HEALTHY"
        assert HealthStatus.DEGRADED == "DEGRADED"
        assert HealthStatus.UNHEALTHY == "UNHEALTHY"

    def test_to_metric_value(self) -> None:
        assert HealthStatus.UNHEALTHY.to_metric_value() == 0
        assert HealthStatus.DEGRADED.to_metric_value() == 1
        assert HealthStatus.HEALTHY.to_metric_value() == 2


@pytest.mark.unit
class TestCircuitBreakerState:
    """Tests for CircuitBreakerState enum."""

    def test_values(self) -> None:
        assert CircuitBreakerState.CLOSED == "CLOSED"
        assert CircuitBreakerState.OPEN == "OPEN"
        assert CircuitBreakerState.HALF_OPEN == "HALF_OPEN"

    def test_to_metric_value(self) -> None:
        assert CircuitBreakerState.CLOSED.to_metric_value() == 0
        assert CircuitBreakerState.HALF_OPEN.to_metric_value() == 1
        assert CircuitBreakerState.OPEN.to_metric_value() == 2


@pytest.mark.unit
class TestErrorType:
    """Tests for ErrorType enum."""

    def test_critical_errors__test_error_type_domain_types_test_enums_77(self) -> None:
        assert ErrorType.AUTH_FAILURE.is_critical() is True
        assert ErrorType.SCHEMA_MISMATCH_GOLD.is_critical() is True
        assert ErrorType.DB_UNAVAILABLE.is_critical() is True
        assert ErrorType.SCHEMA_EVOLUTION.is_critical() is True
        assert ErrorType.LOCK_LOST.is_critical() is True

    def test_recoverable_errors(self) -> None:
        assert ErrorType.RATE_LIMIT.is_recoverable() is True
        assert ErrorType.TIMEOUT.is_recoverable() is True
        assert ErrorType.NETWORK_ERROR.is_recoverable() is True

    def test_data_quality_errors__test_error_type_domain_types_test_enums_89(
        self,
    ) -> None:
        assert ErrorType.SCHEMA_VIOLATION.is_data_quality() is True
        assert ErrorType.INVALID_DATA.is_data_quality() is True
        assert ErrorType.MISSING_REQUIRED_FIELD.is_data_quality() is True
        assert ErrorType.DATA_QUALITY.is_data_quality() is True

    def test_mutual_exclusivity(self) -> None:
        for error_type in ErrorType:
            categories = [
                error_type.is_critical(),
                error_type.is_recoverable(),
                error_type.is_data_quality(),
            ]
            assert sum(categories) == 1, (
                f"{error_type} belongs to {sum(categories)} categories"
            )


@pytest.mark.unit
class TestExecutionContext:
    """Tests for ExecutionContext enum."""

    def test_values(self) -> None:
        assert ExecutionContext.ISOLATED == "isolated"
        assert ExecutionContext.ENRICHER == "enricher"
        assert ExecutionContext.DEPENDENCY == "dependency"

    def test_is_enricher(self) -> None:
        assert ExecutionContext.ENRICHER.is_enricher is True
        assert ExecutionContext.ISOLATED.is_enricher is False
        assert ExecutionContext.DEPENDENCY.is_enricher is False


@pytest.mark.unit
class TestDriftLevel:
    """Tests for DriftLevel enum."""

    def test_values(self) -> None:
        assert DriftLevel.INFO == "INFO"
        assert DriftLevel.CRITICAL == "CRITICAL"


@pytest.mark.unit
class TestCellularityType:
    """Tests for CellularityType enum."""

    def test_values(self) -> None:
        assert CellularityType.ACELLULAR == "acellular"
        assert CellularityType.UNICELLULAR == "unicellular"
        assert CellularityType.MULTICELLULAR == "multicellular"


@pytest.mark.unit
class TestPublicationType:
    """Tests for PublicationType enum."""

    def test_journal_article(self) -> None:
        assert PublicationType.JOURNAL_ARTICLE == "journal-article"

    def test_other(self) -> None:
        assert PublicationType.OTHER == "other"

    def test_all_values_are_kebab_case_or_single_word(self) -> None:
        for pt in PublicationType:
            assert " " not in pt.value, f"{pt} value contains spaces"


@pytest.mark.unit
class TestDataClassification:
    """Tests for DataClassification enum."""

    def test_values(self) -> None:
        assert DataClassification.PUBLIC == "PUBLIC"
        assert DataClassification.INTERNAL == "INTERNAL"
        assert DataClassification.RESTRICTED == "RESTRICTED"


@pytest.mark.unit
class TestQuarantineRecordStatus:
    """Tests for QuarantineRecordStatus enum."""

    def test_values(self) -> None:
        assert QuarantineRecordStatus.NEW == "NEW"
        assert QuarantineRecordStatus.IGNORED == "IGNORED"
        assert QuarantineRecordStatus.REPROCESSED == "REPROCESSED"
