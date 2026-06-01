"""Unit tests for merger_output_mixin — Silver/Gold write helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from bioetl.application.composite.merger_output_mixin import MergeOutputWriterMixin
from bioetl.domain.exceptions import DataQualityError


def _make_mixin(**overrides: object) -> MergeOutputWriterMixin:
    """Build a minimal MergeOutputWriterMixin with mock collaborators."""
    mixin = MergeOutputWriterMixin.__new__(MergeOutputWriterMixin)
    mixin._logger = MagicMock()
    mixin._config = MagicMock()
    mixin._config.output_silver_path = "silver/composite/pub"
    mixin._config.output_gold_path = "gold/pub_enriched"
    mixin._storage = AsyncMock()
    mixin._field_group_registry = None
    mixin._gold_schema = None
    for key, value in overrides.items():
        setattr(mixin, key, value)
    return mixin


@pytest.mark.unit
class TestPathToTableName:
    """Test _path_to_table_name static method."""

    def test_path_to_table_name__strips_silver_prefix__182015f9(self) -> None:
        assert (
            MergeOutputWriterMixin._path_to_table_name("silver/composite/pub")
            == "composite/pub"
        )

    def test_path_to_table_name__strips_gold_prefix__fb4a3fb9(self) -> None:
        assert (
            MergeOutputWriterMixin._path_to_table_name("gold/pub_enriched")
            == "pub_enriched"
        )

    def test_path_to_table_name__strips_bronze_prefix__9d2945e2(self) -> None:
        assert MergeOutputWriterMixin._path_to_table_name("bronze/raw") == "raw"

    def test_handles_backslashes(self) -> None:
        assert (
            MergeOutputWriterMixin._path_to_table_name("silver\\composite\\pub")
            == "composite/pub"
        )

    def test_returns_path_unchanged_when_no_layer(self) -> None:
        assert (
            MergeOutputWriterMixin._path_to_table_name("other/table") == "other/table"
        )


@pytest.mark.unit
class TestCoerceNullColumns:
    """Test _coerce_null_columns for Delta Lake compatibility."""

    def test_coerces_null_columns_to_string(self) -> None:
        mixin = _make_mixin()
        df = pl.DataFrame({"a": [1, 2], "b": [None, None]})
        # Column 'b' has Null type

        result = mixin._coerce_null_columns(df)

        assert result["b"].dtype == pl.String

    def test_leaves_non_null_columns_unchanged(self) -> None:
        mixin = _make_mixin()
        df = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})

        result = mixin._coerce_null_columns(df)

        assert result["a"].dtype == pl.Int64
        assert result["b"].dtype == pl.String


@pytest.mark.unit
class TestWriteMergedSilver:
    """Test _write_merged_silver storage call."""

    @pytest.mark.asyncio
    async def test_writes_records_to_storage(self) -> None:
        mixin = _make_mixin()
        df = pl.DataFrame({"doi": ["10.1/a"]})
        completed_at = datetime(2026, 4, 10, tzinfo=UTC)

        await mixin._write_merged_silver(
            df,
            completed_at=completed_at,
            run_id="r1",
            sources_used=["seed"],
        )

        mixin._storage.write_silver_merged.assert_awaited_once()
        call_kwargs = mixin._storage.write_silver_merged.call_args
        assert call_kwargs[0][0] == "composite/pub"  # table_name after stripping
        assert call_kwargs[1]["run_id"] == "r1"
        assert call_kwargs[1]["completed_at"] == completed_at


@pytest.mark.unit
class TestWriteMergedGold:
    """Test _write_merged_gold with optional trash column filtering."""

    @pytest.mark.asyncio
    async def test_writes_records_to_gold(self) -> None:
        schema = MagicMock()
        mixin = _make_mixin(_gold_schema=schema)
        df = pl.DataFrame({"doi": ["10.1/a"]})
        completed_at = datetime(2026, 4, 10, tzinfo=UTC)

        await mixin._write_merged_gold(
            df,
            completed_at=completed_at,
            run_id="r1",
            sources_used=["seed"],
        )

        mixin._storage.write_gold_merged.assert_awaited_once()
        call_kwargs = mixin._storage.write_gold_merged.call_args.kwargs
        assert call_kwargs["completed_at"] == completed_at
        assert call_kwargs["schema"] is schema

    @pytest.mark.asyncio
    async def test_filters_trash_columns_when_registry_present(self) -> None:
        registry = MagicMock()
        registry.get_trash_columns.return_value = ["_trash_col"]
        mixin = _make_mixin(_field_group_registry=registry, _gold_schema=MagicMock())
        df = pl.DataFrame({"doi": ["10.1/a"], "_trash_col": ["junk"]})

        await mixin._write_merged_gold(df, run_id="r1", sources_used=["seed"])

        # Verify storage received records without trash column
        call_args = mixin._storage.write_gold_merged.call_args
        records = call_args[0][1]
        assert all("_trash_col" not in rec for rec in records)

    @pytest.mark.asyncio
    async def test_missing_gold_schema_fails_before_storage_write(self) -> None:
        """Production composite Gold writes require a registered schema."""
        mixin = _make_mixin()
        df = pl.DataFrame({"doi": ["10.1/a"]})

        with pytest.raises(DataQualityError, match="registered strict schema"):
            await mixin._write_merged_gold(df)

        mixin._storage.write_gold_merged.assert_not_called()
