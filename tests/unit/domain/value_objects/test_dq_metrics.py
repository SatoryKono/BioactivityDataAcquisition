"""Tests for DQ Metrics Value Objects.

Tests for BatchDQMetrics, ColumnStats, and SchemaDriftInfo.
Implements REQ-DQ-001: DQ metrics in Silver metadata.
"""

from __future__ import annotations

import pytest

from bioetl.domain.value_objects.dq_metrics import (
    BatchDQMetrics,
    ColumnStats,
    SchemaDriftInfo,
    _compute_column_stats,
    _extract_numeric_values,
)

pytestmark = pytest.mark.unit


class TestColumnStats:
    """Tests for ColumnStats Value Object."""

    def test_default_values(self) -> None:
        """Test creation with default values."""
        stats = ColumnStats()
        assert stats.null_rate == pytest.approx(0.0)
        assert stats.unique_count is None
        assert stats.min_value is None
        assert stats.max_value is None
        assert stats.mean_value is None

    def test_with_all_values(self) -> None:
        """Test creation with all values provided."""
        stats = ColumnStats(
            null_rate=0.25,
            unique_count=10,
            min_value=1.0,
            max_value=100.0,
            mean_value=50.5,
        )
        assert stats.null_rate == pytest.approx(0.25)
        assert stats.unique_count == 10
        assert stats.min_value == pytest.approx(1.0)
        assert stats.max_value == pytest.approx(100.0)
        assert stats.mean_value == pytest.approx(50.5)

    def test_to_column_metrics(self) -> None:
        """Test conversion to ColumnMetrics model."""
        stats = ColumnStats(
            null_rate=0.1,
            unique_count=5,
            min_value=0.0,
            max_value=10.0,
            mean_value=5.0,
        )
        metrics = stats.to_column_metrics()
        assert metrics.null_rate == pytest.approx(0.1)
        assert metrics.unique_count == 5
        assert metrics.min == pytest.approx(0.0)
        assert metrics.max == pytest.approx(10.0)
        assert metrics.mean == pytest.approx(5.0)

    def test_immutability(self) -> None:
        """Test that ColumnStats is immutable."""
        stats = ColumnStats(null_rate=0.1)
        with pytest.raises(AttributeError):
            stats.null_rate = 0.2  # type: ignore[misc]


class TestSchemaDriftInfo:
    """Tests for SchemaDriftInfo Value Object."""

    def test_default_values(self) -> None:
        """Test creation with default values."""
        drift = SchemaDriftInfo()
        assert drift.status == "info"
        assert drift.new_fields == ()
        assert drift.missing_fields == ()
        assert drift.has_drift is False

    def test_with_new_fields(self) -> None:
        """Test creation with new fields."""
        drift = SchemaDriftInfo(
            status="info",
            new_fields=("field1", "field2"),
        )
        assert drift.new_fields == ("field1", "field2")
        assert drift.has_drift is True

    def test_with_missing_fields(self) -> None:
        """Test creation with missing fields."""
        drift = SchemaDriftInfo(
            status="warn",
            missing_fields=("old_field",),
        )
        assert drift.missing_fields == ("old_field",)
        assert drift.has_drift is True

    def test_list_to_tuple_conversion(self) -> None:
        """Test that lists are converted to tuples for immutability."""
        drift = SchemaDriftInfo(
            status="info",
            new_fields=["field1", "field2"],  # type: ignore[arg-type]
            missing_fields=["old_field"],  # type: ignore[arg-type]
        )
        assert isinstance(drift.new_fields, tuple)
        assert isinstance(drift.missing_fields, tuple)

    def test_to_schema_drift(self) -> None:
        """Test conversion to SchemaDrift model."""
        drift = SchemaDriftInfo(
            status="warn",
            new_fields=("new1", "new2"),
            missing_fields=("old1",),
        )
        schema_drift = drift.to_schema_drift()
        assert schema_drift.status == "warn"
        assert schema_drift.new_fields == ["new1", "new2"]
        assert schema_drift.missing_fields == ["old1"]

    def test_has_drift_false_when_no_changes(self) -> None:
        """Test has_drift is False when no fields changed."""
        drift = SchemaDriftInfo(status="info")
        assert drift.has_drift is False

    def test_immutability(self) -> None:
        """Test that SchemaDriftInfo is immutable."""
        drift = SchemaDriftInfo(status="info")
        with pytest.raises(AttributeError):
            drift.status = "warn"  # type: ignore[misc]


class TestBatchDQMetrics:
    """Tests for BatchDQMetrics Value Object."""

    def test_default_values(self) -> None:
        """Test creation with default values."""
        metrics = BatchDQMetrics()
        assert metrics.total_records == 0
        assert metrics.valid_records == 0
        assert metrics.error_records == 0
        assert metrics.warning_records == 0
        assert metrics.column_stats == {}
        assert metrics.schema_drift is None
        assert metrics.validation_errors == ()

    def test_error_rate_calculation(self) -> None:
        """Test error rate calculation."""
        metrics = BatchDQMetrics(
            total_records=100,
            valid_records=95,
            error_records=5,
        )
        assert metrics.error_rate == pytest.approx(0.05)

    def test_error_rate_zero_total(self) -> None:
        """Test error rate is 0 when total_records is 0."""
        metrics = BatchDQMetrics(total_records=0, error_records=0)
        assert metrics.error_rate == pytest.approx(0.0)

    def test_validation_passed(self) -> None:
        """Test validation_passed property."""
        passed = BatchDQMetrics(total_records=10, error_records=0)
        assert passed.validation_passed is True

        failed = BatchDQMetrics(total_records=10, error_records=1)
        assert failed.validation_passed is False

    def test_validation_errors_list_to_tuple(self) -> None:
        """Test that validation_errors list is converted to tuple."""
        metrics = BatchDQMetrics(
            total_records=10,
            validation_errors=["error1", "error2"],  # type: ignore[arg-type]
        )
        assert isinstance(metrics.validation_errors, tuple)
        assert metrics.validation_errors == ("error1", "error2")

    def test_to_dq_summary_basic(self) -> None:
        """Test conversion to DQSummary with basic values."""
        metrics = BatchDQMetrics(
            total_records=100,
            valid_records=95,
            error_records=5,
            warning_records=3,
        )
        summary = metrics.to_dq_summary()
        assert summary.total_records == 100
        assert summary.valid_records == 95
        assert summary.error_records == 5
        assert summary.warning_records == 3
        assert summary.error_rate == pytest.approx(0.05)
        assert summary.validation_passed is False

    def test_to_dq_summary_with_column_stats(self) -> None:
        """Test conversion to DQSummary includes column metrics."""
        column_stats = {
            "name": ColumnStats(null_rate=0.1, unique_count=50),
            "value": ColumnStats(null_rate=0.0, min_value=1.0, max_value=100.0),
        }
        metrics = BatchDQMetrics(
            total_records=100,
            valid_records=100,
            column_stats=column_stats,
        )
        summary = metrics.to_dq_summary()
        assert len(summary.column_metrics) == 2
        assert summary.column_metrics["name"].null_rate == pytest.approx(0.1)
        assert summary.column_metrics["name"].unique_count == 50
        assert summary.column_metrics["value"].min == pytest.approx(1.0)
        assert summary.column_metrics["value"].max == pytest.approx(100.0)

    def test_to_dq_summary_with_schema_drift(self) -> None:
        """Test conversion to DQSummary includes schema drift."""
        drift = SchemaDriftInfo(
            status="warn",
            new_fields=("new_col",),
        )
        metrics = BatchDQMetrics(
            total_records=100,
            valid_records=100,
            schema_drift=drift,
        )
        summary = metrics.to_dq_summary()
        assert summary.schema_drift is not None
        assert summary.schema_drift.status == "warn"
        assert summary.schema_drift.new_fields == ["new_col"]

    def test_to_dq_summary_no_drift_when_no_changes(self) -> None:
        """Test DQSummary has no schema_drift when drift has no changes."""
        drift = SchemaDriftInfo(status="info")  # No fields changed
        metrics = BatchDQMetrics(
            total_records=100,
            valid_records=100,
            schema_drift=drift,
        )
        summary = metrics.to_dq_summary()
        assert summary.schema_drift is None

    def test_immutability(self) -> None:
        """Test that BatchDQMetrics is immutable."""
        metrics = BatchDQMetrics(total_records=100)
        with pytest.raises(AttributeError):
            metrics.total_records = 200  # type: ignore[misc]


class TestBatchDQMetricsFromRecords:
    """Tests for BatchDQMetrics.from_records() factory method."""

    def test_empty_records(self) -> None:
        """Test with empty records list."""
        metrics = BatchDQMetrics.from_records([])
        assert metrics.total_records == 0
        assert metrics.valid_records == 0
        assert metrics.column_stats == {}

    def test_basic_records(self) -> None:
        """Test with basic records."""
        records = [
            {"name": "A", "value": 1},
            {"name": "B", "value": 2},
            {"name": "C", "value": 3},
        ]
        metrics = BatchDQMetrics.from_records(records)
        assert metrics.total_records == 3
        assert metrics.valid_records == 3
        assert metrics.error_records == 0

    def test_with_error_count(self) -> None:
        """Test with error count specified."""
        records = [
            {"name": "A", "value": 1},
            {"name": "B", "value": 2},
        ]
        metrics = BatchDQMetrics.from_records(records, error_count=1)
        assert metrics.total_records == 2
        assert metrics.valid_records == 1
        assert metrics.error_records == 1
        assert metrics.error_rate == pytest.approx(0.5)

    def test_with_validation_errors(self) -> None:
        """Test with validation errors."""
        records = [{"name": "A"}]
        metrics = BatchDQMetrics.from_records(
            records,
            error_count=1,
            validation_errors=["Missing field 'value'"],
        )
        assert metrics.validation_errors == ("Missing field 'value'",)

    def test_with_schema_drift(self) -> None:
        """Test with schema drift info."""
        records = [{"name": "A"}]
        drift = SchemaDriftInfo(status="info", new_fields=("new_col",))
        metrics = BatchDQMetrics.from_records(records, schema_drift=drift)
        assert metrics.schema_drift is not None
        assert metrics.schema_drift.new_fields == ("new_col",)

    def test_column_stats_computed(self) -> None:
        """Test that column stats are computed from records."""
        records = [
            {"name": "A", "value": 10.0},
            {"name": "B", "value": 20.0},
            {"name": None, "value": 30.0},  # null name
        ]
        metrics = BatchDQMetrics.from_records(records)

        # Check name column stats
        name_stats = metrics.column_stats.get("name")
        assert name_stats is not None
        assert name_stats.null_rate == pytest.approx(1 / 3, rel=0.01)
        assert name_stats.unique_count == 2  # "A" and "B"

        # Check value column stats
        value_stats = metrics.column_stats.get("value")
        assert value_stats is not None
        assert value_stats.null_rate == pytest.approx(0.0)
        assert value_stats.min_value == pytest.approx(10.0)
        assert value_stats.max_value == pytest.approx(30.0)
        assert value_stats.mean_value == pytest.approx(20.0)

    def test_internal_fields_excluded(self) -> None:
        """Test that internal fields (starting with _) are excluded from stats."""
        records = [
            {"name": "A", "_run_id": "123", "_ingestion_ts": "2024-01-01"},
        ]
        metrics = BatchDQMetrics.from_records(records)
        assert "name" in metrics.column_stats
        assert "_run_id" not in metrics.column_stats
        assert "_ingestion_ts" not in metrics.column_stats


class TestComputeColumnStats:
    """Tests for _compute_column_stats helper function."""

    def test_empty_records(self) -> None:
        """Test with empty records list."""
        result = _compute_column_stats([])
        assert result == {}

    def test_all_null_column(self) -> None:
        """Test column with all null values."""
        records = [
            {"col": None},
            {"col": None},
        ]
        result = _compute_column_stats(records)
        assert result["col"].null_rate == pytest.approx(1.0)
        assert result["col"].unique_count == 0

    def test_numeric_column(self) -> None:
        """Test numeric column statistics."""
        records = [
            {"value": 10},
            {"value": 20},
            {"value": 30},
        ]
        result = _compute_column_stats(records)
        stats = result["value"]
        assert stats.min_value == pytest.approx(10.0)
        assert stats.max_value == pytest.approx(30.0)
        assert stats.mean_value == pytest.approx(20.0)

    def test_mixed_types_column(self) -> None:
        """Test column with mixed types (only numerics counted)."""
        records = [
            {"col": 10},
            {"col": "text"},
            {"col": 30},
        ]
        result = _compute_column_stats(records)
        stats = result["col"]
        # Only 10 and 30 are numeric
        assert stats.min_value == pytest.approx(10.0)
        assert stats.max_value == pytest.approx(30.0)

    def test_nan_inf_excluded(self) -> None:
        """Test that NaN and Inf values are excluded from numeric stats."""
        records = [
            {"value": 10},
            {"value": float("nan")},
            {"value": float("inf")},
            {"value": 20},
        ]
        result = _compute_column_stats(records)
        stats = result["value"]
        assert stats.min_value == pytest.approx(10.0)
        assert stats.max_value == pytest.approx(20.0)
        assert stats.mean_value == pytest.approx(15.0)


class TestExtractNumericValues:
    """Tests for _extract_numeric_values helper function."""

    def test_empty_list(self) -> None:
        """Test with empty list."""
        assert _extract_numeric_values([]) == []

    def test_all_numeric(self) -> None:
        """Test with all numeric values."""
        result = _extract_numeric_values([1, 2.5, 3])
        assert result == pytest.approx([1.0, 2.5, 3.0])

    def test_mixed_types(self) -> None:
        """Test with mixed types."""
        result = _extract_numeric_values([1, "text", 2, None, 3])
        assert result == pytest.approx([1.0, 2.0, 3.0])

    def test_bool_excluded(self) -> None:
        """Test that boolean values are excluded."""
        result = _extract_numeric_values([1, True, False, 2])
        assert result == pytest.approx([1.0, 2.0])

    def test_nan_inf_excluded(self) -> None:
        """Test that NaN and Inf are excluded."""
        result = _extract_numeric_values([1, float("nan"), float("inf"), 2])
        assert result == pytest.approx([1.0, 2.0])

    def test_negative_inf_excluded(self) -> None:
        """Test that negative Inf is excluded."""
        result = _extract_numeric_values([1, float("-inf"), 2])
        assert result == pytest.approx([1.0, 2.0])
