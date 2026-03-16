"""Unit tests for merger_orchestration — load_merge_inputs and execute_merge_workflow."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from bioetl.application.composite.merger_input_mixin import _PreparedSeedDataframe
from bioetl.application.composite.merger_orchestration import (
    MergeInputContext,
    load_merge_inputs,
)
from bioetl.domain.composite.config import DependencyConfig, EnricherConfig
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
)


def _enricher_config(pipeline: str) -> EnricherConfig:
    return EnricherConfig(pipeline=pipeline, join_keys=("doi",))


def _make_host() -> MagicMock:
    """Build a mock host object implementing MergeWorkflowContext."""
    host = MagicMock()
    seed_df = pl.DataFrame({"doi": ["10.1/a"]})
    host._prepare_seed_dataframe = AsyncMock(
        return_value=_PreparedSeedDataframe(
            seed_df=seed_df,
            records_from_seed=1,
            effective_seed_pipeline="chembl_compound",
        )
    )
    host._load_enricher_dataframes = AsyncMock(
        return_value=(
            {"crossref_publication": pl.DataFrame({"doi": ["10.1/a"], "title": ["T"]})},
            ["crossref_publication"],
        )
    )
    host._load_dependency_dataframes = AsyncMock(return_value=({}, []))
    return host


@pytest.mark.unit
class TestMergeInputContext:
    """Test MergeInputContext dataclass."""

    def test_fields_accessible(self) -> None:
        ctx = MergeInputContext(
            seed_df=pl.DataFrame(),
            records_from_seed=0,
            effective_seed_pipeline=None,
            sources_used=["seed"],
            enricher_dfs={},
            dependency_dfs={},
        )
        assert ctx.records_from_seed == 0
        assert ctx.sources_used == ["seed"]


@pytest.mark.unit
class TestLoadMergeInputs:
    """Test load_merge_inputs orchestration helper."""

    @pytest.mark.asyncio
    async def test_assembles_context_from_host(self) -> None:
        host = _make_host()
        enrichers = [_enricher_config("crossref_publication")]
        enrichment_results = {
            "crossref_publication": EnrichmentResult(
                enricher_name="crossref_publication",
                status=EnrichmentStatus.SUCCESS,
            )
        }

        ctx = await load_merge_inputs(
            host,
            seed_table="silver/chembl",
            seed_pipeline="chembl_compound",
            enrichers=enrichers,
            enrichment_results=enrichment_results,
            dependencies=None,
            dependency_results=None,
        )

        assert isinstance(ctx, MergeInputContext)
        assert ctx.records_from_seed == 1
        assert ctx.effective_seed_pipeline == "chembl_compound"
        assert "seed" in ctx.sources_used
        assert "crossref_publication" in ctx.sources_used

    @pytest.mark.asyncio
    async def test_includes_dependency_sources(self) -> None:
        host = _make_host()
        host._load_dependency_dataframes = AsyncMock(
            return_value=(
                {"dep_a": pl.DataFrame({"x": [1]})},
                ["dep_a"],
            )
        )
        deps = [
            DependencyConfig(
                pipeline="dep_a", join_keys=("doi",), silver_table="silver/dep_a"
            )
        ]

        ctx = await load_merge_inputs(
            host,
            seed_table="silver/chembl",
            seed_pipeline="chembl_compound",
            enrichers=[],
            enrichment_results={},
            dependencies=deps,
            dependency_results={
                "dep_a": DependencyResult(
                    pipeline_name="dep_a",
                    status=DependencyStatus.SUCCESS,
                    records_silver=1,
                )
            },
        )

        assert "dep_a" in ctx.sources_used
        assert "dep_a" in ctx.dependency_dfs

    @pytest.mark.asyncio
    async def test_sources_start_with_seed(self) -> None:
        host = _make_host()
        host._load_enricher_dataframes = AsyncMock(return_value=({}, []))

        ctx = await load_merge_inputs(
            host,
            seed_table="silver/s",
            seed_pipeline=None,
            enrichers=[],
            enrichment_results={},
            dependencies=None,
            dependency_results=None,
        )

        assert ctx.sources_used[0] == "seed"
