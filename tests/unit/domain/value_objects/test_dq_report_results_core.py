"""Unit tests for DQ core result value objects."""

from __future__ import annotations

import pytest

from bioetl.domain.value_objects.dq_report_enums import DQCheckStatus
from bioetl.domain.value_objects.dq_report_results_core import (
    CategoricalDistribution,
    DriftLevel,
    EncodingValidationResult,
    SchemaDriftResult,
    SchemaSnapshotResult,
    TypeConformanceResult,
    UniquenessResult,
)


@pytest.mark.unit
class TestSchemaSnapshotResult:
    """Tests for SchemaSnapshotResult."""

    def test_list_to_tuple_conversion(self) -> None:
        """Test that list fields are converted to tuples in __post_init__."""
        result = SchemaSnapshotResult(
            fields_detected=5,
            schema={"col1": "int"},
            new_fields_since_last_run=["f1", "f2"],  # type: ignore[arg-type]
            missing_fields_since_last_run=["f3"],  # type: ignore[arg-type]
        )
        assert isinstance(result.new_fields_since_last_run, tuple)
        assert result.new_fields_since_last_run == ("f1", "f2")
        assert isinstance(result.missing_fields_since_last_run, tuple)
        assert result.missing_fields_since_last_run == ("f3",)


@pytest.mark.unit
class TestEncodingValidationResult:
    """Tests for EncodingValidationResult."""

    def test_list_to_tuple_conversion(self) -> None:
        """Test that list fields are converted to tuples in __post_init__."""
        result = EncodingValidationResult(
            encoding_errors=2,
            invalid_utf8_records=[10, 20],  # type: ignore[arg-type]
        )
        assert isinstance(result.invalid_utf8_records, tuple)
        assert result.invalid_utf8_records == (10, 20)


@pytest.mark.unit
class TestUniquenessResult:
    """Tests for UniquenessResult."""

    def test_instantiation(self) -> None:
        """Test basic instantiation."""
        result = UniquenessResult(
            primary_key="id",
            unique_count=100,
            total_count=100,
            duplicate_rate=0.0,
            status=DQCheckStatus.PASS,
        )
        assert result.primary_key == "id"
        assert result.unique_count == 100
        assert result.total_count == 100
        assert result.duplicate_rate == pytest.approx(0.0)
        assert result.status == DQCheckStatus.PASS


@pytest.mark.unit
class TestTypeConformanceResult:
    """Tests for TypeConformanceResult."""

    def test_list_to_tuple_conversion(self) -> None:
        """Test that list fields are converted to tuples in __post_init__."""
        result = TypeConformanceResult(
            schema_version="1.0",
            pandera_passed=False,
            errors=["err1", "err2"],  # type: ignore[arg-type]
        )
        assert isinstance(result.errors, tuple)
        assert result.errors == ("err1", "err2")


@pytest.mark.unit
class TestCategoricalDistribution:
    """Tests for CategoricalDistribution."""

    def test_list_to_tuple_conversion(self) -> None:
        """Test that list fields are converted to tuples in __post_init__."""
        result = CategoricalDistribution(
            top_values=[{"val": "a", "count": 10}],  # type: ignore[arg-type]
            cardinality=1,
        )
        assert isinstance(result.top_values, tuple)
        assert result.top_values == ({"val": "a", "count": 10},)


@pytest.mark.unit
class TestSchemaDriftResult:
    """Tests for SchemaDriftResult."""

    def test_list_to_tuple_conversion(self) -> None:
        """Test that list fields are converted to tuples in __post_init__."""
        result = SchemaDriftResult(
            drift_level=DriftLevel.INFO,
            new_fields=["f1"],  # type: ignore[arg-type]
            missing_fields=["f2"],  # type: ignore[arg-type]
            type_changes=[{"field": "f3", "from": "int", "to": "str"}],  # type: ignore[arg-type]
        )
        assert isinstance(result.new_fields, tuple)
        assert result.new_fields == ("f1",)
        assert isinstance(result.missing_fields, tuple)
        assert result.missing_fields == ("f2",)
        assert isinstance(result.type_changes, tuple)
        assert result.type_changes == ({"field": "f3", "from": "int", "to": "str"},)
