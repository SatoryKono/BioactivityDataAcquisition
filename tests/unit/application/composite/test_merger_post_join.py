"""Unit tests for merger_post_join — finalization and persist helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from unittest.mock import patch

import polars as pl
import pytest

from bioetl.application.composite.merger_post_join import (
    MergePostJoinContext,
    finalize_merged_dataframe,
    finalize_post_join_context,
    persist_and_build_result,
)
from bioetl.domain.composite.config import EnricherConfig
from bioetl.domain.composite.result import EnrichmentResult, EnrichmentStatus


def _enricher_config(pipeline: str) -> EnricherConfig:
    return EnricherConfig(pipeline=pipeline, join_keys=("doi",))


def _enrichment_result(
    name: str, status: EnrichmentStatus = EnrichmentStatus.SUCCESS
) -> EnrichmentResult:
    return EnrichmentResult(enricher_name=name, status=status)


def _make_host() -> MagicMock:
    """Build a mock host implementing MergePostJoinWorkflowContext."""
    host = MagicMock()
    host._logger = MagicMock()
    host._conflict_resolver = MagicMock()
    host._conflict_resolver.resolve_conflicts.side_effect = lambda df, **kw: df
    host._order_service = MagicMock()
    host._order_service.order_columns.side_effect = lambda df: df
    host._run_cross_validation = MagicMock(
        return_value=(pl.DataFrame({"doi": ["10.1/a"]}), None, [])
    )
    host._apply_field_mappings = MagicMock(side_effect=lambda df: df)
    host._add_lineage = MagicMock(side_effect=lambda df, **kw: df)
    host._drop_excluded_fields = MagicMock(side_effect=lambda df: df)
    host._count_enriched_records = MagicMock(return_value=1)
    host._write_outputs = AsyncMock()
    host._build_merge_result = MagicMock()
    return host


@pytest.mark.unit
class TestMergePostJoinContext:
    """Test MergePostJoinContext dataclass."""

    def test_fields_accessible(self) -> None:
        ctx = MergePostJoinContext(
            merged_df=pl.DataFrame(),
            records_merged=0,
            records_enriched=0,
            cv_stats=None,
            quarantine_payloads=[],
        )
        assert ctx.records_merged == 0
        assert ctx.quarantine_payloads == []


@pytest.mark.unit
class TestFinalizeMergedDataframe:
    """Test finalize_merged_dataframe pipeline."""

    def test_calls_all_finalization_steps(self) -> None:
        host = _make_host()
        df = pl.DataFrame({"doi": ["10.1/a"]})
        enrichers = [_enricher_config("e1")]
        enrichment_results = {"e1": _enrichment_result("e1")}

        result = finalize_merged_dataframe(
            host,
            merged_df=df,
            enrichers=enrichers,
            enrichment_results=enrichment_results,
            effective_seed_pipeline="seed_pub",
            run_id="run-1",
            metadata_timestamp=None,
            sources_used=["seed"],
            dependency_results=None,
            enricher_dfs={"e1": pl.DataFrame()},
        )

        host._conflict_resolver.resolve_conflicts.assert_called_once()
        host._apply_field_mappings.assert_called_once()
        host._add_lineage.assert_called_once()
        host._drop_excluded_fields.assert_called_once()
        host._order_service.order_columns.assert_called_once()
        assert isinstance(result, pl.DataFrame)


@pytest.mark.unit
class TestFinalizePostJoinContext:
    """Test finalize_post_join_context."""

    def test_produces_context_with_counts(self) -> None:
        host = _make_host()
        df = pl.DataFrame({"doi": ["10.1/a"]})
        enrichers = [_enricher_config("e1")]
        enrichment_results = {"e1": _enrichment_result("e1")}

        ctx = finalize_post_join_context(
            host,
            merged_df=df,
            enrichers=enrichers,
            enrichment_results=enrichment_results,
            effective_seed_pipeline="seed_pub",
            run_id="run-1",
            metadata_timestamp=None,
            sources_used=["seed"],
            dependency_results=None,
            enricher_dfs={},
        )

        assert isinstance(ctx, MergePostJoinContext)
        assert ctx.records_merged >= 0
        assert ctx.cv_stats is None


@pytest.mark.unit
class TestPersistAndBuildResult:
    """Test persist_and_build_result writes and builds result."""

    @pytest.mark.asyncio
    async def test_writes_outputs_and_returns_result(self) -> None:
        host = _make_host()
        host._build_merge_result.return_value = MagicMock(records_merged=1)
        df = pl.DataFrame({"doi": ["10.1/a"]})
        enrichers = [_enricher_config("e1")]
        metadata_timestamp = datetime(2026, 4, 10, tzinfo=UTC)

        result = await persist_and_build_result(
            host,
            merged_df=df,
            enrichers=enrichers,
            records_merged=1,
            records_from_seed=1,
            records_enriched=0,
            sources_used=["seed"],
            cv_stats=None,
            quarantine_payloads=[],
            metadata_timestamp=metadata_timestamp,
            run_id="run-1",
            started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            started_monotonic=10.0,
        )

        host._write_outputs.assert_awaited_once()
        assert host._write_outputs.await_args.kwargs["metadata_timestamp"] == (
            metadata_timestamp
        )
        host._build_merge_result.assert_called_once()
        assert result.records_merged == 1

    @pytest.mark.asyncio
    async def test_duration_is_positive(self) -> None:
        host = _make_host()
        host._build_merge_result.return_value = MagicMock()
        df = pl.DataFrame({"doi": ["10.1/a"]})
        started_at = datetime(2020, 1, 1, tzinfo=UTC)

        with patch(
            "bioetl.application.composite.merger_post_join.derive_completion_timestamp",
            return_value=(started_at, 3.5),
        ):
            await persist_and_build_result(
                host,
                merged_df=df,
                enrichers=[],
                records_merged=0,
                records_from_seed=0,
                records_enriched=0,
                sources_used=[],
                cv_stats=None,
                quarantine_payloads=[],
                metadata_timestamp=None,
                run_id="run-1",
                started_at=started_at,
                started_monotonic=5.0,
            )

        call_kwargs = host._build_merge_result.call_args[1]
        assert call_kwargs["duration_seconds"] == pytest.approx(3.5)
