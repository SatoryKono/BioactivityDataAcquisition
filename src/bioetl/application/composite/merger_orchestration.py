"""Internal orchestration helpers for ``MergeService``."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from bioetl.application.composite.merger_post_join import (
    MergePostJoinWorkflowContext,
    finalize_post_join_context,
    persist_and_build_result,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    import polars as pl

    from bioetl.application.composite.join_planner import JoinPlannerService
    from bioetl.domain.composite.config import DependencyConfig, EnricherConfig
    from bioetl.domain.composite.result import (
        DependencyResult,
        EnrichmentResult,
        MergeResult,
    )


@dataclass(frozen=True, slots=True)
class MergeInputContext:
    """Resolved seed, dependency, and enricher inputs for one merge run."""

    seed_df: pl.DataFrame
    records_from_seed: int
    effective_seed_pipeline: str | None
    sources_used: list[str]
    enricher_dfs: dict[str, pl.DataFrame]
    dependency_dfs: dict[str, pl.DataFrame]


class MergeWorkflowContext(MergePostJoinWorkflowContext, Protocol):
    """Subset of MergeService API required by orchestration helpers."""

    _join_planner: JoinPlannerService

    async def _prepare_seed_dataframe(
        self,
        seed_table: str,
        seed_pipeline: str | None,
    ) -> tuple[pl.DataFrame, int, str | None]: ...

    async def _load_enricher_dataframes(
        self,
        enrichers: Sequence[EnricherConfig],
        enrichment_results: dict[str, EnrichmentResult],
    ) -> tuple[dict[str, pl.DataFrame], list[str]]: ...

    async def _load_dependency_dataframes(
        self,
        dependencies: Sequence[DependencyConfig] | None,
        dependency_results: dict[str, DependencyResult] | None,
    ) -> tuple[dict[str, pl.DataFrame], list[str]]: ...

    async def _apply_dependency_joins_if_needed(
        self,
        merged_df: pl.DataFrame,
        dependency_dfs: dict[str, pl.DataFrame],
        dependencies: Sequence[DependencyConfig] | None,
        seed_pipeline: str | None,
    ) -> pl.DataFrame: ...


async def load_merge_inputs(
    host: MergeWorkflowContext,
    *,
    seed_table: str,
    seed_pipeline: str | None,
    enrichers: Sequence[EnricherConfig],
    enrichment_results: dict[str, EnrichmentResult],
    dependencies: Sequence[DependencyConfig] | None,
    dependency_results: dict[str, DependencyResult] | None,
) -> MergeInputContext:
    """Load seed, dependency, and enricher frames for merge orchestration."""
    (
        seed_df,
        records_from_seed,
        effective_seed_pipeline,
    ) = await host._prepare_seed_dataframe(seed_table, seed_pipeline)
    sources_used = ["seed"]

    enricher_dfs, enricher_sources = await host._load_enricher_dataframes(
        enrichers,
        enrichment_results,
    )
    sources_used.extend(enricher_sources)

    dependency_dfs, dependency_sources = await host._load_dependency_dataframes(
        dependencies,
        dependency_results,
    )
    sources_used.extend(dependency_sources)

    return MergeInputContext(
        seed_df=seed_df,
        records_from_seed=records_from_seed,
        effective_seed_pipeline=effective_seed_pipeline,
        sources_used=sources_used,
        enricher_dfs=enricher_dfs,
        dependency_dfs=dependency_dfs,
    )


async def execute_merge_workflow(
    host: MergeWorkflowContext,
    *,
    seed_table: str,
    enrichers: Sequence[EnricherConfig],
    enrichment_results: dict[str, EnrichmentResult],
    run_id: str,
    seed_pipeline: str | None = None,
    dependencies: Sequence[DependencyConfig] | None = None,
    dependency_results: dict[str, DependencyResult] | None = None,
) -> MergeResult:
    """Execute the full composite merge workflow for ``MergeService``."""
    started_at = datetime.now(tz=UTC)
    loaded = await load_merge_inputs(
        host,
        seed_table=seed_table,
        seed_pipeline=seed_pipeline,
        enrichers=enrichers,
        enrichment_results=enrichment_results,
        dependencies=dependencies,
        dependency_results=dependency_results,
    )

    merged_df = await host._join_planner.apply_joins(
        seed_df=loaded.seed_df,
        enricher_dfs=loaded.enricher_dfs,
        enrichers=enrichers,
        seed_pipeline=loaded.effective_seed_pipeline,
    )
    merged_df = await host._apply_dependency_joins_if_needed(
        merged_df=merged_df,
        dependency_dfs=loaded.dependency_dfs,
        dependencies=dependencies,
        seed_pipeline=loaded.effective_seed_pipeline,
    )
    post_join_context = finalize_post_join_context(
        host,
        merged_df=merged_df,
        enrichers=enrichers,
        enrichment_results=enrichment_results,
        effective_seed_pipeline=loaded.effective_seed_pipeline,
        run_id=run_id,
        sources_used=loaded.sources_used,
        dependency_results=dependency_results,
        enricher_dfs=loaded.enricher_dfs,
    )
    return await persist_and_build_result(
        host,
        merged_df=post_join_context.merged_df,
        enrichers=enrichers,
        records_merged=post_join_context.records_merged,
        records_from_seed=loaded.records_from_seed,
        records_enriched=post_join_context.records_enriched,
        sources_used=loaded.sources_used,
        cv_stats=post_join_context.cv_stats,
        quarantine_payloads=post_join_context.quarantine_payloads,
        run_id=run_id,
        started_at=started_at,
    )
