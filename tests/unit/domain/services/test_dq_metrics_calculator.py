"""Unit tests for DQMetricsCalculator."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.dq_metrics_calculator import (
    DQMetricsCalculator,
    DQMetricsInput,
)
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics


@pytest.fixture
def sample_records():
    """Create sample records for testing."""
    return [
        {"entity_id": "CHEMBL123", "value": 5.5, "name": "Test 1"},
        {"entity_id": "CHEMBL456", "value": 7.2, "name": "Test 2"},
        {"entity_id": "CHEMBL789", "value": None, "name": "Test 3"},
    ]


@pytest.mark.unit
class TestDQMetricsCalculator:
    """Tests for DQMetricsCalculator."""

    def test_calculate_returns_batch_dq_metrics(self, sample_records):
        """Test calculate returns BatchDQMetrics."""
        calculator = DQMetricsCalculator()
        input_data = DQMetricsInput(records=sample_records)

        result = calculator.calculate(input_data)

        assert isinstance(result, BatchDQMetrics)
        assert result.total_records == 3
        assert result.valid_records == 3

    def test_calculate_with_quarantined_count(self, sample_records):
        """Test calculate with quarantined_count."""
        calculator = DQMetricsCalculator()
        input_data = DQMetricsInput(
            records=sample_records,
            quarantined_count=2,
        )

        result = calculator.calculate(input_data)

        assert result.error_records == 2

    def test_calculate_with_validation_errors(self, sample_records):
        """Test calculate with validation_errors."""
        calculator = DQMetricsCalculator()
        input_data = DQMetricsInput(
            records=sample_records,
            validation_errors=["Error 1", "Error 2"],
        )

        result = calculator.calculate(input_data)

        assert len(result.validation_errors) == 2
        assert "Error 1" in result.validation_errors
        assert "Error 2" in result.validation_errors

    def test_calculate_column_stats(self, sample_records):
        """Test calculate computes column statistics."""
        calculator = DQMetricsCalculator()
        input_data = DQMetricsInput(records=sample_records)

        result = calculator.calculate(input_data)

        # Should have column stats
        assert "entity_id" in result.column_stats
        assert "value" in result.column_stats
        assert "name" in result.column_stats

        # value column should have numeric stats
        value_stats = result.column_stats["value"]
        assert value_stats.min_value is not None
        assert value_stats.max_value is not None

    def test_detect_schema_drift_no_existing_schema(self, sample_records):
        """Test _detect_schema_drift returns None when no existing schema."""
        calculator = DQMetricsCalculator()

        result = calculator._detect_schema_drift(
            records=sample_records,
            existing_fields=None,
        )

        assert result is None

    def test_detect_schema_drift_empty_records(self):
        """Test _detect_schema_drift returns None for empty records."""
        calculator = DQMetricsCalculator()

        result = calculator._detect_schema_drift(
            records=[],
            existing_fields={"entity_id", "value"},
        )

        assert result is None

    def test_detect_schema_drift_no_drift(self, sample_records):
        """Test _detect_schema_drift returns None when no drift."""
        calculator = DQMetricsCalculator()
        existing_fields = {"entity_id", "value", "name"}

        result = calculator._detect_schema_drift(
            records=sample_records,
            existing_fields=existing_fields,
        )

        assert result is None

    def test_detect_schema_drift_info_status_for_minor_changes(self, sample_records):
        """Test _detect_schema_drift returns 'info' for minor changes."""
        calculator = DQMetricsCalculator()
        # Missing one field, but it's a metadata field (starts with _)
        existing_fields = {"entity_id", "value", "name", "_run_id"}

        result = calculator._detect_schema_drift(
            records=sample_records,
            existing_fields=existing_fields,
        )

        assert result is not None
        assert result.status == "info"
        assert "_run_id" in result.missing_fields

    def test_detect_schema_drift_warn_status_for_many_new_fields(self):
        """Test _detect_schema_drift returns 'warn' for >3 new fields."""
        calculator = DQMetricsCalculator()
        records = [
            {
                "entity_id": "CHEMBL123",
                "new_field_1": "a",
                "new_field_2": "b",
                "new_field_3": "c",
                "new_field_4": "d",
            }
        ]
        existing_fields = {"entity_id"}

        result = calculator._detect_schema_drift(
            records=records,
            existing_fields=existing_fields,
        )

        assert result is not None
        assert result.status == "warn"
        assert len(result.new_fields) == 4

    def test_detect_schema_drift_critical_status_for_missing_business_fields(self):
        """Test _detect_schema_drift returns 'critical' for missing business fields."""
        calculator = DQMetricsCalculator()
        records = [{"entity_id": "CHEMBL123"}]
        existing_fields = {"entity_id", "important_field"}  # Business field missing

        result = calculator._detect_schema_drift(
            records=records,
            existing_fields=existing_fields,
        )

        assert result is not None
        assert result.status == "critical"
        assert "important_field" in result.missing_fields

    def test_calculate_with_schema_drift(self):
        """Test calculate includes schema drift info."""
        calculator = DQMetricsCalculator()
        records = [{"entity_id": "CHEMBL123", "new_field": "value"}]
        existing_fields = {"entity_id"}

        input_data = DQMetricsInput(
            records=records,
            existing_schema_fields=existing_fields,
        )

        result = calculator.calculate(input_data)

        assert result.schema_drift is not None
        assert "new_field" in result.schema_drift.new_fields


@pytest.mark.unit
class TestDQMetricsInput:
    """Tests for DQMetricsInput dataclass."""

    def test_dq_metrics_input_defaults(self):
        """Test DQMetricsInput has correct defaults."""
        records = [{"a": 1}]
        input_data = DQMetricsInput(records=records)

        assert input_data.records == records
        assert input_data.existing_schema_fields is None
        assert input_data.quarantined_count == 0
        assert input_data.validation_errors is None

    def test_dq_metrics_input_is_frozen(self):
        """Test DQMetricsInput is frozen (immutable)."""
        input_data = DQMetricsInput(records=[{"a": 1}])

        with pytest.raises(AttributeError):
            input_data.records = []  # type: ignore

    def test_dq_metrics_input_all_fields(self):
        """Test DQMetricsInput with all fields."""
        records = [{"a": 1}]
        existing_fields = {"a", "b"}
        validation_errors = ["Error 1"]

        input_data = DQMetricsInput(
            records=records,
            existing_schema_fields=existing_fields,
            quarantined_count=5,
            validation_errors=validation_errors,
        )

        assert input_data.records == records
        assert input_data.existing_schema_fields == existing_fields
        assert input_data.quarantined_count == 5
        assert input_data.validation_errors == validation_errors
