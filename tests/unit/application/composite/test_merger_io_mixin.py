"""Unit tests for merger_io_mixin — cross-validation, output, and result assembly."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from bioetl.application.composite.merger_io_mixin import MergeIOMixin
from bioetl.domain.composite.config import DependencyConfig, EnricherConfig


def _empty_field_coverage(_df: pl.DataFrame) -> dict[str, int]:
    return {}


def _zero_fully_enriched(_df: pl.DataFrame, _enrichers: object) -> int:
    return 0


def _make_mixin(**overrides: object) -> MergeIOMixin:
    """Build a minimal MergeIOMixin with mock collaborators."""
    mixin = MergeIOMixin.__new__(MergeIOMixin)
    mixin._logger = MagicMock()
    mixin._config = MagicMock()
    mixin._config.output_silver_path = "silver/composite/pub"
    mixin._config.output_gold_path = "gold/pub_enriched"
    mixin._field_group_registry = None
    mixin._cross_validator = None
    mixin._gold_schema = None
    mixin._join_planner = MagicMock()
    mixin._calculate_field_coverage = _empty_field_coverage
    mixin._count_fully_enriched = _zero_fully_enriched
    mixin._storage = AsyncMock()
    mixin._delta_reader = None
    mixin._renamer = MagicMock()
    for key, value in overrides.items():
        setattr(mixin, key, value)
    return mixin


def _enricher_config(pipeline: str) -> EnricherConfig:
    return EnricherConfig(pipeline=pipeline, join_keys=("doi",))


def _dependency_config(pipeline: str) -> DependencyConfig:
    return DependencyConfig(
        pipeline=pipeline, join_keys=("doi",), silver_table="silver/dep"
    )


@pytest.mark.unit
class TestApplyDependencyJoinsIfNeeded:
    """Test _apply_dependency_joins_if_needed."""

    @pytest.mark.asyncio
    async def test_returns_unchanged_when_no_dependencies(self) -> None:
        mixin = _make_mixin()
        df = pl.DataFrame({"a": [1]})

        result = await mixin._apply_dependency_joins_if_needed(
            merged_df=df, dependency_dfs={}, dependencies=None, seed_pipeline=None
        )

        assert result is df

    @pytest.mark.asyncio
    async def test_returns_unchanged_when_empty_dfs(self) -> None:
        mixin = _make_mixin()
        df = pl.DataFrame({"a": [1]})
        deps = [_dependency_config("dep_a")]

        result = await mixin._apply_dependency_joins_if_needed(
            merged_df=df, dependency_dfs={}, dependencies=deps, seed_pipeline=None
        )

        assert result is df

    @pytest.mark.asyncio
    async def test_calls_join_planner_when_data_present(self) -> None:
        mixin = _make_mixin()
        merged = pl.DataFrame({"doi": ["10.1/a"]})
        dep_df = pl.DataFrame({"doi": ["10.1/a"], "extra": [42]})
        deps = [_dependency_config("dep_a")]
        mixin._join_planner.apply_dependency_joins = AsyncMock(
            return_value=pl.DataFrame({"doi": ["10.1/a"], "extra": [42]})
        )

        result = await mixin._apply_dependency_joins_if_needed(
            merged_df=merged,
            dependency_dfs={"dep_a": dep_df},
            dependencies=deps,
            seed_pipeline=None,
        )

        mixin._join_planner.apply_dependency_joins.assert_awaited_once()
        assert "extra" in result.columns


@pytest.mark.unit
class TestRunCrossValidation:
    """Test _run_cross_validation with and without a cross-validator."""

    def test_returns_unchanged_when_no_validator(self) -> None:
        mixin = _make_mixin(_cross_validator=None)
        df = pl.DataFrame({"x": [1]})

        result_df, stats, quarantine = mixin._run_cross_validation(
            merged_df=df,
            enrichers=[_enricher_config("e1")],
            enricher_dfs={"e1": pl.DataFrame()},
            effective_seed_pipeline="seed_pub",
        )

        assert result_df is df
        assert stats is None
        assert quarantine == []

    def test_returns_unchanged_when_no_seed_pipeline(self) -> None:
        mixin = _make_mixin(_cross_validator=MagicMock())
        df = pl.DataFrame({"x": [1]})

        result_df, stats, _ = mixin._run_cross_validation(
            merged_df=df,
            enrichers=[_enricher_config("e1")],
            enricher_dfs={"e1": pl.DataFrame()},
            effective_seed_pipeline=None,
        )

        assert result_df is df
        assert stats is None

    def test_filters_quarantined_rows_from_persisted_output(self) -> None:
        mixin = _make_mixin(_cross_validator=MagicMock())
        validated_df = pl.DataFrame(
            {
                "doi": ["10.1/a", "10.1/b"],
                "_cv_quarantine": [False, True],
            }
        )
        cv_stats = MagicMock()
        mixin._cross_validator.validate.return_value = (validated_df, cv_stats)

        result_df, stats, quarantine = mixin._run_cross_validation(
            merged_df=pl.DataFrame({"doi": ["10.1/a", "10.1/b"]}),
            enrichers=[_enricher_config("e1")],
            enricher_dfs={"e1": pl.DataFrame({"doi": ["10.1/a"]})},
            effective_seed_pipeline="seed_pub",
        )

        assert stats is cv_stats
        assert result_df.to_dicts() == [{"doi": "10.1/a", "_cv_quarantine": False}]
        assert quarantine == [{"doi": "10.1/b", "_cv_quarantine": True}]


@pytest.mark.unit
class TestExtractQuarantinePayloads:
    """Test static _extract_quarantine_payloads."""

    def test_empty_when_no_column(self) -> None:
        df = pl.DataFrame({"a": [1, 2]})
        assert MergeIOMixin._extract_quarantine_payloads(df) == []

    def test_empty_when_no_quarantined_rows(self) -> None:
        df = pl.DataFrame({"a": [1], "_cv_quarantine": [False]})
        assert MergeIOMixin._extract_quarantine_payloads(df) == []

    def test_extracts_quarantined_rows(self) -> None:
        df = pl.DataFrame({"a": [1, 2, 3], "_cv_quarantine": [False, True, True]})
        payloads = MergeIOMixin._extract_quarantine_payloads(df)
        assert len(payloads) == 2
        assert payloads[0]["a"] == 2


@pytest.mark.unit
class TestDropQuarantinedRows:
    """Test static _drop_quarantined_rows."""

    def test_returns_unchanged_when_marker_missing(self) -> None:
        df = pl.DataFrame({"a": [1, 2]})
        assert MergeIOMixin._drop_quarantined_rows(df) is df

    def test_removes_quarantined_rows(self) -> None:
        df = pl.DataFrame({"a": [1, 2], "_cv_quarantine": [False, True]})
        result = MergeIOMixin._drop_quarantined_rows(df)
        assert result.to_dicts() == [{"a": 1, "_cv_quarantine": False}]


@pytest.mark.unit
class TestBuildMergeResult:
    """Test _build_merge_result assembly."""

    def test_builds_result_with_all_fields(self) -> None:
        mixin = _make_mixin()
        df = pl.DataFrame({"doi": ["10.1/a"]})

        result = mixin._build_merge_result(
            merged_df=df,
            enrichers=[_enricher_config("e1")],
            records_merged=1,
            records_from_seed=1,
            records_enriched=0,
            sources_used=["seed", "e1"],
            duration_seconds=1.5,
            cv_stats=None,
            quarantine_payloads=[],
        )

        assert result.records_merged == 1
        assert result.records_from_seed == 1
        assert result.output_silver_path == "silver/composite/pub"
        assert result.output_gold_path == "gold/pub_enriched"
        assert result.duration_seconds == pytest.approx(1.5)
