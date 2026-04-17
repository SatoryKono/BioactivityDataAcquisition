"""Unit tests for merger_metrics_mixin — lineage, exclusion, and coverage."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.merger_metrics_mixin import MergeMetricsRecorderMixin
from bioetl.domain.composite.config import EnricherConfig
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
)


def _make_mixin(**overrides: object) -> MergeMetricsRecorderMixin:
    """Build a minimal MergeMetricsRecorderMixin with mock collaborators."""
    mixin = MergeMetricsRecorderMixin.__new__(MergeMetricsRecorderMixin)
    mixin._logger = MagicMock()
    mixin._config = MagicMock()
    mixin._config.exclude_fields = ()
    for key, value in overrides.items():
        setattr(mixin, key, value)
    return mixin


def _enricher_config(pipeline: str) -> EnricherConfig:
    return EnricherConfig(pipeline=pipeline, join_keys=("doi",))


@pytest.mark.unit
class TestAddLineage:
    """Test _add_lineage semantic metadata injection."""

    def test_adds_only_semantic_composite_columns(self) -> None:
        mixin = _make_mixin()
        df = pl.DataFrame({"doi": ["10.1/a"]})
        enrichment_results = {
            "chembl_compound": EnrichmentResult(
                enricher_name="chembl_compound", status=EnrichmentStatus.SUCCESS
            )
        }

        result = mixin._add_lineage(
            df,
            enrichment_results,
            run_id="run-1",
            metadata_timestamp=None,
            sources_used=["seed"],
        )

        assert "_source_providers" in result.columns
        assert "_enrichment_status" in result.columns
        assert "_composite_run_id" not in result.columns
        assert "_lineage_created_at" not in result.columns

    def test_includes_dependency_results_in_status(self) -> None:
        mixin = _make_mixin()
        df = pl.DataFrame({"doi": ["10.1/a"]})
        dep_results = {
            "dep_a": DependencyResult(
                pipeline_name="dep_a",
                status=DependencyStatus.SUCCESS,
                records_silver=1,
            )
        }

        result = mixin._add_lineage(
            df,
            enrichment_results={},
            run_id="run-2",
            metadata_timestamp=datetime(2026, 4, 10, 0, 0, 0, tzinfo=UTC),
            sources_used=["seed"],
            dependency_results=dep_results,
        )

        status_str = result["_enrichment_status"][0]
        assert "dep_a" in status_str
        assert "success" in status_str
        assert "_lineage_created_at" not in result.columns


@pytest.mark.unit
class TestDropExcludedFields:
    """Test _drop_excluded_fields with glob patterns."""

    def test_no_exclusion_when_empty(self) -> None:
        mixin = _make_mixin()
        df = pl.DataFrame({"a": [1], "b": [2]})

        result = mixin._drop_excluded_fields(df)

        assert result.columns == ["a", "b"]

    def test_drops_matching_glob_pattern(self) -> None:
        config = MagicMock()
        config.exclude_fields = ("_internal_*",)
        mixin = _make_mixin(_config=config)
        df = pl.DataFrame({"doi": [1], "_internal_flag": [True], "_internal_id": [99]})

        result = mixin._drop_excluded_fields(df)

        assert "doi" in result.columns
        assert "_internal_flag" not in result.columns
        assert "_internal_id" not in result.columns

    def test_no_drop_when_pattern_matches_nothing(self) -> None:
        config = MagicMock()
        config.exclude_fields = ("nonexistent_*",)
        mixin = _make_mixin(_config=config)
        df = pl.DataFrame({"a": [1], "b": [2]})

        result = mixin._drop_excluded_fields(df)

        assert result.columns == ["a", "b"]


@pytest.mark.unit
class TestCountEnrichedRecords:
    """Test _count_enriched_records prefix-based counting."""

    def test_counts_rows_with_enricher_columns(self) -> None:
        mixin = _make_mixin()
        df = pl.DataFrame(
            {
                "doi": ["a", "b", "c"],
                "chembl.compound.name": ["X", None, "Z"],
            }
        )
        enrichers = [_enricher_config("chembl_compound")]

        count = mixin._count_enriched_records(df, enrichers)

        assert count == 2

    def test_zero_when_no_matching_columns(self) -> None:
        mixin = _make_mixin()
        df = pl.DataFrame({"doi": ["a", "b"]})
        enrichers = [_enricher_config("chembl_compound")]

        count = mixin._count_enriched_records(df, enrichers)

        assert count == 0

    def test_fallback_prefix_for_unparseable_pipeline(self) -> None:
        mixin = _make_mixin()
        df = pl.DataFrame({"doi": ["a"], "mypipeline_val": [1]})
        enrichers = [_enricher_config("mypipeline")]

        count = mixin._count_enriched_records(df, enrichers)

        assert count == 1


@pytest.mark.unit
class TestCountFullyEnriched:
    """Test _count_fully_enriched placeholder."""

    def test_always_returns_zero(self) -> None:
        mixin = _make_mixin()
        df = pl.DataFrame({"a": [1, 2]})
        assert mixin._count_fully_enriched(df, []) == 0


@pytest.mark.unit
class TestCalculateFieldCoverage:
    """Test _calculate_field_coverage non-null ratio computation."""

    def test_empty_dataframe_returns_empty_dict(self) -> None:
        mixin = _make_mixin()
        df = pl.DataFrame({"a": pl.Series([], dtype=pl.Int64)})
        assert mixin._calculate_field_coverage(df) == {}

    def test_full_coverage(self) -> None:
        mixin = _make_mixin()
        df = pl.DataFrame({"a": [1, 2], "b": [3, 4]})
        coverage = mixin._calculate_field_coverage(df)
        assert coverage["a"] == pytest.approx(1.0)
        assert coverage["b"] == pytest.approx(1.0)

    def test_partial_coverage(self) -> None:
        mixin = _make_mixin()
        df = pl.DataFrame({"a": [1, None, None], "b": [1, 2, 3]})
        coverage = mixin._calculate_field_coverage(df)
        assert coverage["a"] == pytest.approx(1 / 3, abs=0.01)
        assert coverage["b"] == pytest.approx(1.0)

    def test_skips_private_columns(self) -> None:
        mixin = _make_mixin()
        df = pl.DataFrame({"a": [1], "_private": [2]})
        coverage = mixin._calculate_field_coverage(df)
        assert "a" in coverage
        assert "_private" not in coverage
