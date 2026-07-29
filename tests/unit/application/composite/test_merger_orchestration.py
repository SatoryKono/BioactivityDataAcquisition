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
"""Unit tests for merger_orchestration helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from unittest.mock import patch

import polars as pl
import pytest

from bioetl.application.composite.merger_input_mixin import _PreparedSeedDataframe
from bioetl.application.composite.merger_orchestration import (
    MergeExecutionContext,
    MergeInputContext,
    build_merge_execution_request,
    prepare_merge_execution_context,
    resolve_merge_metadata_timestamp,
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
class TestMergeExecutionRequestHelpers:
    """Test canonical request/context helpers for merge execution."""

    def test_build_merge_execution_request_when_called_then_binds_all_fields(
        self,
    ) -> None:
        request = build_merge_execution_request(
            seed_table="silver/seed",
            seed_pipeline="seed_pipeline",
            enrichers=[],
            enrichment_results={},
            run_id="run-123",
            metadata_timestamp=datetime(2026, 4, 10, 0, 0, 0, tzinfo=UTC),
        )

        assert request.seed_table == "silver/seed"
        assert request.seed_pipeline == "seed_pipeline"
        assert request.run_id == "run-123"
        assert request.metadata_timestamp == datetime(2026, 4, 10, 0, 0, 0, tzinfo=UTC)

    def test_resolve_merge_metadata_timestamp_when_none_then_returns_none(self) -> None:
        assert resolve_merge_metadata_timestamp(None) is None

    def test_resolve_merge_metadata_timestamp_when_iso_date_then_returns_utc_midnight(
        self,
    ) -> None:
        assert resolve_merge_metadata_timestamp("2026-04-10") == datetime(
            2026,
            4,
            10,
            0,
            0,
            0,
            tzinfo=UTC,
        )

    @pytest.mark.asyncio
    async def test_prepare_merge_execution_context_when_called_then_loads_inputs_once(
        self,
    ) -> None:
        host = _make_host()
        request = build_merge_execution_request(
            seed_table="silver/chembl",
            seed_pipeline="chembl_compound",
            enrichers=[],
            enrichment_results={},
            run_id="run-ctx",
        )

        started_at = datetime(2026, 4, 12, 12, 0, tzinfo=UTC)
        with patch(
            "bioetl.application.composite.merger_orchestration.capture_runtime_timing_anchor",
            return_value=(started_at, 10.0),
        ):
            execution_context = await prepare_merge_execution_context(host, request)

        assert isinstance(execution_context, MergeExecutionContext)
        assert execution_context.request is request
        assert execution_context.loaded_inputs.records_from_seed == 1
        assert execution_context.started_at == started_at
        assert execution_context.started_monotonic == pytest.approx(10.0)
        host._prepare_seed_dataframe.assert_awaited_once_with(
            "silver/chembl",
            "chembl_compound",
        )


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
