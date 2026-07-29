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
"""Unit tests for dependency_key_resolvers — SeedKeyResolver and ChainedKeyResolver."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from bioetl.application.composite.dependency_key_resolvers import (
    ChainedKeyResolver,
    SeedKeyResolver,
    create_chained_key_resolver,
    create_seed_key_resolver,
)
from bioetl.domain.composite.config import DependencyConfig


def _dep_config(
    pipeline: str = "dep_a",
    join_keys: tuple[str, ...] = ("doi",),
    key_source: str | None = None,
    silver_table: str | None = "silver/dep",
    key_filter: str | None = None,
) -> DependencyConfig:
    return DependencyConfig(
        pipeline=pipeline,
        join_keys=join_keys,
        key_source=key_source,
        silver_table=silver_table,
        key_filter=key_filter,
    )


@pytest.mark.unit
class TestSeedKeyResolver:
    """Test SeedKeyResolver pass-through behaviour."""

    @pytest.mark.asyncio
    async def test_returns_seed_keys_with_canonical_normalization(self) -> None:
        logger = MagicMock()
        resolver = create_seed_key_resolver(logger)
        seed_keys = pl.DataFrame({"doi": [" 10.1/A ", "10.1/b"]})
        dep = _dep_config()

        result = await resolver.resolve(
            dependency=dep,
            seed_keys=seed_keys,
            dep_config_lookup={},
            delta_reader=None,
        )

        assert result.to_dict(as_series=False) == {"doi": ["10.1/a", "10.1/b"]}

    @pytest.mark.asyncio
    async def test_logs_debug_message(self) -> None:
        logger = MagicMock()
        resolver = create_seed_key_resolver(logger)

        await resolver.resolve(
            dependency=_dep_config(),
            seed_keys=pl.DataFrame({"doi": []}),
            dep_config_lookup={},
            delta_reader=None,
        )

        logger.debug.assert_called_once()


@pytest.mark.unit
class TestChainedKeyResolver:
    """Test ChainedKeyResolver chained dependency key resolution."""

    @pytest.mark.asyncio
    async def test_raises_without_delta_reader(self) -> None:
        logger = MagicMock()
        resolver = create_chained_key_resolver(logger)
        dep = _dep_config(key_source="source_dep")

        with pytest.raises(ValueError, match="requires delta_reader"):
            await resolver.resolve(
                dependency=dep,
                seed_keys=pl.DataFrame(),
                dep_config_lookup={},
                delta_reader=None,
            )

    @pytest.mark.asyncio
    async def test_raises_for_unknown_key_source(self) -> None:
        logger = MagicMock()
        resolver = create_chained_key_resolver(logger)
        dep = _dep_config(key_source="nonexistent")
        delta_reader = AsyncMock()

        with pytest.raises(ValueError, match=r"unknown.*key_source"):
            await resolver.resolve(
                dependency=dep,
                seed_keys=pl.DataFrame(),
                dep_config_lookup={},
                delta_reader=delta_reader,
            )

    @pytest.mark.asyncio
    async def test_raises_when_source_has_no_silver_table(self) -> None:
        logger = MagicMock()
        resolver = create_chained_key_resolver(logger)
        dep = _dep_config(key_source="source_dep")
        source_dep = _dep_config(pipeline="source_dep", silver_table=None)
        delta_reader = AsyncMock()

        with pytest.raises(ValueError, match="no silver_table configured"):
            await resolver.resolve(
                dependency=dep,
                seed_keys=pl.DataFrame(),
                dep_config_lookup={"source_dep": source_dep},
                delta_reader=delta_reader,
            )

    @pytest.mark.asyncio
    async def test_falls_back_to_seed_on_file_not_found(self) -> None:
        logger = MagicMock()
        resolver = create_chained_key_resolver(logger)
        dep = _dep_config(key_source="source_dep")
        source_dep = _dep_config(pipeline="source_dep", silver_table="silver/src")
        delta_reader = AsyncMock()
        delta_reader.read_table.side_effect = FileNotFoundError("not found")
        seed_keys = pl.DataFrame({"doi": ["10.1/a"]})

        result = await resolver.resolve(
            dependency=dep,
            seed_keys=seed_keys,
            dep_config_lookup={"source_dep": source_dep},
            delta_reader=delta_reader,
        )

        assert result.equals(seed_keys)
        logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_falls_back_to_seed_on_empty_table(self) -> None:
        logger = MagicMock()
        resolver = create_chained_key_resolver(logger)
        dep = _dep_config(key_source="source_dep")
        source_dep = _dep_config(pipeline="source_dep", silver_table="silver/src")
        delta_reader = AsyncMock()
        # Return an empty PyArrow table
        empty_arrow = pl.DataFrame({"doi": pl.Series([], dtype=pl.Utf8)}).to_arrow()
        delta_reader.read_table.return_value = empty_arrow
        seed_keys = pl.DataFrame({"doi": ["fallback"]})

        result = await resolver.resolve(
            dependency=dep,
            seed_keys=seed_keys,
            dep_config_lookup={"source_dep": source_dep},
            delta_reader=delta_reader,
        )

        assert result.equals(seed_keys)

    @pytest.mark.asyncio
    async def test_resolves_keys_from_source_table(self) -> None:
        logger = MagicMock()
        resolver = create_chained_key_resolver(logger)
        dep = _dep_config(key_source="source_dep")
        source_dep = _dep_config(pipeline="source_dep", silver_table="silver/src")
        delta_reader = AsyncMock()
        source_df = pl.DataFrame({"doi": ["10.1/x", "10.1/y"]})
        delta_reader.read_table.return_value = source_df.to_arrow()

        result = await resolver.resolve(
            dependency=dep,
            seed_keys=pl.DataFrame(),
            dep_config_lookup={"source_dep": source_dep},
            delta_reader=delta_reader,
        )

        assert len(result) == 2
        assert "doi" in result.columns

    @pytest.mark.asyncio
    async def test_normalizes_chained_source_keys_before_returning(self) -> None:
        logger = MagicMock()
        resolver = create_chained_key_resolver(logger)
        dep = _dep_config(key_source="source_dep")
        source_dep = _dep_config(pipeline="source_dep", silver_table="silver/src")
        delta_reader = AsyncMock()
        source_df = pl.DataFrame({"doi": [" 10.1/X ", "10.1/x"]})
        delta_reader.read_table.return_value = source_df.to_arrow()

        result = await resolver.resolve(
            dependency=dep,
            seed_keys=pl.DataFrame(),
            dep_config_lookup={"source_dep": source_dep},
            delta_reader=delta_reader,
        )

        assert result.to_dict(as_series=False) == {"doi": ["10.1/x", "10.1/x"]}

    @pytest.mark.asyncio
    async def test_seed_resolver_normalizes_compound_join_key_families(self) -> None:
        logger = MagicMock()
        resolver = create_seed_key_resolver(logger)
        dep = _dep_config(join_keys=("doi", "title", "pmid", "uniprot_accession"))
        seed_keys = pl.DataFrame(
            {
                "doi": [" 10.1/ABC "],
                "title": ["  Mixed Case Title  "],
                "pmid": [" PMID:12345 "],
                "uniprot_accession": [" P12345 "],
            }
        )

        result = await resolver.resolve(
            dependency=dep,
            seed_keys=seed_keys,
            dep_config_lookup={},
            delta_reader=None,
        )

        assert result.to_dict(as_series=False) == {
            "doi": ["10.1/abc"],
            "title": ["Mixed Case Title"],
            "pmid": ["12345"],
            "uniprot_accession": ["P12345"],
        }

    @pytest.mark.asyncio
    async def test_validates_join_key_exists(self) -> None:
        logger = MagicMock()
        resolver = create_chained_key_resolver(logger)
        dep = _dep_config(key_source="source_dep", join_keys=("missing_col",))
        source_dep = _dep_config(pipeline="source_dep", silver_table="silver/src")
        delta_reader = AsyncMock()
        source_df = pl.DataFrame({"doi": ["10.1/x"]})
        delta_reader.read_table.return_value = source_df.to_arrow()

        with pytest.raises(ValueError, match=r"Column.*not found"):
            await resolver.resolve(
                dependency=dep,
                seed_keys=pl.DataFrame(),
                dep_config_lookup={"source_dep": source_dep},
                delta_reader=delta_reader,
            )


@pytest.mark.unit
class TestFactoryFunctions:
    """Test create_seed_key_resolver and create_chained_key_resolver."""

    def test_create_seed_key_resolver(self) -> None:
        logger = MagicMock()
        resolver = create_seed_key_resolver(logger)
        assert isinstance(resolver, SeedKeyResolver)

    def test_create_chained_key_resolver(self) -> None:
        logger = MagicMock()
        resolver = create_chained_key_resolver(logger)
        assert isinstance(resolver, ChainedKeyResolver)
