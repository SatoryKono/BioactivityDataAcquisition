"""Focused unit tests for silver_statistics_helpers."""

from __future__ import annotations

import polars as pl
import pytest

from bioetl.application.services.dq.silver_statistics_helpers import (
    check_content_hash_integrity_stats,
    check_null_rates_stats,
    check_schema_drift_stats,
    check_uniqueness_stats,
    detect_type_changes,
    profile_categorical_column,
    profile_numeric_column,
    value_distribution_to_dict,
)
from bioetl.domain.value_objects.dq_report import (
    CategoricalDistribution,
    DQCheckStatus,
    DriftLevel,
    NumericDistribution,
    ValueDistributionResult,
)


@pytest.mark.unit
class TestSilverStatisticsHelpers:
    """Direct tests for pure helper functions."""

    def test_detect_type_changes_only_reports_changed_shared_fields(self) -> None:
        result = detect_type_changes(
            current={"id": "Int64", "title": "String", "new": "Boolean"},
            previous={"id": "Int64", "title": "Utf8", "old": "String"},
        )

        assert result == [{"field": "title", "from": "Utf8", "to": "String"}]

    def test_check_null_rates_stats_handles_empty_dataframe(self) -> None:
        df = pl.DataFrame(
            {"id": [], "name": []}, schema={"id": pl.Int64, "name": pl.String}
        )

        results, overall = check_null_rates_stats(df)

        assert overall == pytest.approx(0.0)
        assert [item.column_name for item in results] == ["id", "name"]
        assert all(item.null_rate == pytest.approx(0.0) for item in results)
        assert all(item.status == DQCheckStatus.PASS for item in results)

    def test_check_uniqueness_stats_warns_when_primary_keys_missing(self) -> None:
        df = pl.DataFrame({"entity_id": ["e1", "e2"]})

        result = check_uniqueness_stats(df, ["missing_id"], (RuntimeError,))

        assert result.status == DQCheckStatus.WARN
        assert result.primary_key == "missing_id"
        assert (
            result.column_stats["_note"]["message"] == "Primary key columns not found"
        )

    def test_check_uniqueness_stats_calculates_duplicate_rate_and_column_stats(
        self,
    ) -> None:
        df = pl.DataFrame({"entity_id": ["e1", "e1", "e2"], "source": ["a", "a", "b"]})

        result = check_uniqueness_stats(df, ["entity_id"], (RuntimeError,))

        assert result.status == DQCheckStatus.WARN
        assert result.unique_count == 2
        assert result.total_count == 3
        assert result.duplicate_rate == round(1 / 3, 4)
        assert "entity_id" in result.column_stats

    def test_check_schema_drift_stats_handles_absent_previous_schema(self) -> None:
        df = pl.DataFrame({"entity_id": ["e1"], "score": [1.0]})

        result = check_schema_drift_stats(df, None)

        assert result.drift_level == DriftLevel.INFO
        assert result.status == DQCheckStatus.PASS
        assert result.new_fields == ()
        assert result.missing_fields == ()

    def test_check_schema_drift_stats_marks_missing_fields_as_critical(self) -> None:
        df = pl.DataFrame({"entity_id": ["e1"], "score": [1.0]})

        result = check_schema_drift_stats(
            df,
            previous_schema={"entity_id": "String", "title": "String"},
        )

        assert result.drift_level == DriftLevel.CRITICAL
        assert result.status == DQCheckStatus.WARN
        assert result.missing_fields == ("title",)

    def test_check_content_hash_integrity_stats_covers_none_and_collision_paths(
        self,
    ) -> None:
        missing_hash = check_content_hash_integrity_stats(5, None)
        collisions = check_content_hash_integrity_stats(5, 2)

        assert missing_hash.records_checked == 0
        assert missing_hash.status == DQCheckStatus.PASS
        assert collisions.records_checked == 5
        assert collisions.hash_collisions == 2
        assert collisions.status == DQCheckStatus.WARN

    def test_profile_numeric_column_returns_distribution_for_non_empty_values(
        self,
    ) -> None:
        df = pl.DataFrame({"score": [1.0, None, 3.0, 5.0]})

        result = profile_numeric_column(df, "score", (RuntimeError,))

        assert result is not None
        assert result.min == pytest.approx(1.0)
        assert result.max == pytest.approx(5.0)
        assert result.median == pytest.approx(3.0)

    def test_profile_numeric_column_returns_none_for_all_null_values(self) -> None:
        df = pl.DataFrame({"score": [None, None]})

        result = profile_numeric_column(df, "score", (RuntimeError,))

        assert result is None

    def test_profile_categorical_column_builds_top_values(self) -> None:
        df = pl.DataFrame({"category": ["a", "a", "b", None]})

        result = profile_categorical_column(df, "category", (RuntimeError,))

        assert result is not None
        assert result.cardinality == 3
        normalized = {item["value"]: item["count"] for item in result.top_values}
        assert normalized["a"] == 2
        assert normalized["b"] == 1

    def test_value_distribution_to_dict_serializes_numeric_and_categorical_sections(
        self,
    ) -> None:
        payload = ValueDistributionResult(
            numeric_columns={
                "score": NumericDistribution(
                    min=1.0,
                    max=5.0,
                    mean=3.0,
                    std=2.0,
                    median=3.0,
                )
            },
            categorical_columns={
                "category": CategoricalDistribution(
                    top_values=(
                        {"value": "a", "count": 2, "pct": 0.5},
                        {"value": "b", "count": 1, "pct": 0.25},
                    ),
                    cardinality=2,
                )
            },
            status=DQCheckStatus.PASS,
        )

        result = value_distribution_to_dict(payload)

        assert result["status"] == DQCheckStatus.PASS.value
        assert result["numeric_columns"]["score"]["mean"] == pytest.approx(3.0)
        assert result["categorical_columns"]["category"]["cardinality"] == 2
        assert (
            result["categorical_columns"]["category"]["top_values"][0]["value"] == "a"
        )
