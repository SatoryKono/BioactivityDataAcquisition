# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for merger_input_mixin — input loading for MergeService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from bioetl.application.composite.merger_input_mixin import (
    _MergeInputLoaderMixin,
    _PreparedSeedDataframe,
)
from bioetl.domain.composite.config import DependencyConfig, EnricherConfig
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
)
from bioetl.domain.exceptions import StorageError


def _make_mixin(**overrides: object) -> _MergeInputLoaderMixin:
    """Build a minimal _MergeInputLoaderMixin with mock collaborators."""
    mixin = _MergeInputLoaderMixin.__new__(_MergeInputLoaderMixin)
    mixin._logger = MagicMock()
    mixin._storage = AsyncMock()
    mixin._delta_reader = None
    mixin._renamer = MagicMock()
    mixin._config = MagicMock()
    for key, value in overrides.items():
        setattr(mixin, key, value)
    return mixin


def _enricher_config(pipeline: str, silver_table: str | None = None) -> EnricherConfig:
    return EnricherConfig(
        pipeline=pipeline,
        join_keys=("doi",),
        silver_table=silver_table,
    )


def _enrichment_result(
    name: str, status: EnrichmentStatus = EnrichmentStatus.SUCCESS
) -> EnrichmentResult:
    return EnrichmentResult(enricher_name=name, status=status)


def _dependency_config(
    pipeline: str,
    silver_table: str | None = "silver/dep",
) -> DependencyConfig:
    return DependencyConfig(
        pipeline=pipeline,
        join_keys=("doi",),
        silver_table=silver_table,
    )


def _dependency_result(
    name: str, status: DependencyStatus = DependencyStatus.SUCCESS
) -> DependencyResult:
    return DependencyResult(pipeline_name=name, status=status, records_silver=1)


@pytest.mark.unit
class TestReadOptionalMergeInput:
    """Test _read_optional_merge_input graceful degradation."""

    @pytest.mark.asyncio
    async def test_returns_dataframe_on_success(self) -> None:
        mixin = _make_mixin()
        expected = pl.DataFrame({"a": [1, 2]})
        mixin._read_silver_table = AsyncMock(return_value=expected)

        result = await mixin._read_optional_merge_input(
            pipeline="chembl_compound", table="silver/chembl", role="enricher"
        )

        assert result is not None
        assert result.shape == (2, 1)

    @pytest.mark.asyncio
    async def test_returns_none_on_storage_error(self) -> None:
        mixin = _make_mixin()
        mixin._read_silver_table = AsyncMock(side_effect=StorageError("disk fail"))

        result = await mixin._read_optional_merge_input(
            pipeline="chembl_compound", table="silver/chembl", role="enricher"
        )

        assert result is None
        mixin._logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_on_value_error(self) -> None:
        mixin = _make_mixin()
        mixin._read_silver_table = AsyncMock(side_effect=ValueError("bad data"))

        result = await mixin._read_optional_merge_input(
            pipeline="p", table="t", role="enricher"
        )

        assert result is None


@pytest.mark.unit
class TestPrepareSeedDataframe:
    """Test _prepare_seed_dataframe with and without pipeline renaming."""

    @pytest.mark.asyncio
    async def test_no_pipeline_returns_unqualified(self) -> None:
        mixin = _make_mixin()
        raw = pl.DataFrame({"doi": ["10.1/a"], "title": ["T1"]})
        mixin._read_silver_table = AsyncMock(return_value=raw)

        result = await mixin._prepare_seed_dataframe("silver/seed", seed_pipeline=None)

        assert isinstance(result, _PreparedSeedDataframe)
        assert result.records_from_seed == 1
        # No pipeline inference possible from "silver/seed" → effective_seed_pipeline is None
        assert result.effective_seed_pipeline is None

    @pytest.mark.asyncio
    async def test_with_pipeline_renames_columns(self) -> None:
        mixin = _make_mixin()
        raw = pl.DataFrame({"doi": ["10.1/a"]})
        mixin._read_silver_table = AsyncMock(return_value=raw)
        mixin._renamer.rename_dataframe.return_value = pl.DataFrame(
            {"chembl.compound.doi": ["10.1/a"]}
        )

        result = await mixin._prepare_seed_dataframe(
            "silver/chembl_compound", seed_pipeline="chembl_compound"
        )

        assert result.effective_seed_pipeline == "chembl_compound"
        mixin._renamer.rename_dataframe.assert_called_once()


@pytest.mark.unit
class TestLoadEnricherDataframes:
    """Test _load_enricher_dataframes filters by enrichment success."""

    @pytest.mark.asyncio
    async def test_loads_only_successful_enrichers(self) -> None:
        mixin = _make_mixin()
        enrichers = [
            _enricher_config("chembl_compound", silver_table="silver/chembl"),
            _enricher_config("crossref_publication"),
        ]
        results = {
            "chembl_compound": _enrichment_result("chembl_compound"),
            "crossref_publication": _enrichment_result(
                "crossref_publication", EnrichmentStatus.FAILED
            ),
        }
        df = pl.DataFrame({"x": [1]})
        mixin._read_optional_merge_input = AsyncMock(return_value=df)

        dfs, sources = await mixin._load_enricher_dataframes(enrichers, results)

        assert "chembl_compound" in dfs
        assert "crossref_publication" not in dfs
        assert sources == ["chembl_compound"]

    @pytest.mark.asyncio
    async def test_empty_when_all_failed(self) -> None:
        mixin = _make_mixin()
        enrichers = [_enricher_config("p1")]
        results = {"p1": _enrichment_result("p1", EnrichmentStatus.FAILED)}

        dfs, sources = await mixin._load_enricher_dataframes(enrichers, results)

        assert dfs == {}
        assert sources == []


@pytest.mark.unit
class TestLoadDependencyDataframes:
    """Test _load_dependency_dataframes."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_dependencies(self) -> None:
        mixin = _make_mixin()
        dfs, sources = await mixin._load_dependency_dataframes(None, None)
        assert dfs == {}
        assert sources == []

    @pytest.mark.asyncio
    async def test_loads_successful_dependencies(self) -> None:
        mixin = _make_mixin()
        deps = [_dependency_config("dep_a")]
        dep_results = {"dep_a": _dependency_result("dep_a")}
        df = pl.DataFrame({"col": [1]})
        mixin._read_optional_merge_input = AsyncMock(return_value=df)

        dfs, sources = await mixin._load_dependency_dataframes(deps, dep_results)

        assert "dep_a" in dfs
        assert sources == ["dep_a"]


@pytest.mark.unit
class TestReadSilverTable:
    """Test _read_silver_table fallback behaviour."""

    @pytest.mark.asyncio
    async def test_uses_delta_reader_when_available(self) -> None:
        delta_reader = AsyncMock()
        arrow_table = pl.DataFrame({"id": [1, 2]}).to_arrow()
        delta_reader.read_table.return_value = arrow_table
        mixin = _make_mixin(_delta_reader=delta_reader)

        result = await mixin._read_silver_table("silver/test")

        assert isinstance(result, pl.DataFrame)
        assert len(result) == 2
        delta_reader.read_table.assert_awaited_once_with("silver/test")

    @pytest.mark.asyncio
    async def test_falls_back_to_storage_when_no_delta_reader(self) -> None:
        storage = AsyncMock()
        storage.read_silver.return_value = [{"id": 1}]
        mixin = _make_mixin(_storage=storage, _delta_reader=None)

        result = await mixin._read_silver_table("silver/my_table")

        assert len(result) == 1
        storage.read_silver.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_empty_df_when_storage_returns_empty(self) -> None:
        storage = AsyncMock()
        storage.read_silver.return_value = []
        mixin = _make_mixin(_storage=storage, _delta_reader=None)

        result = await mixin._read_silver_table("silver/empty")

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_explicit_none_silver_reader_disables_storage_fallback(self) -> None:
        storage = AsyncMock()
        storage.read_silver.return_value = [{"id": 1}]
        mixin = _make_mixin(_storage=storage, _delta_reader=None, _silver_reader=None)

        with pytest.raises(
            RuntimeError, match="requires delta_reader or silver_reader"
        ):
            await mixin._read_silver_table("silver/my_table")

        storage.read_silver.assert_not_called()
