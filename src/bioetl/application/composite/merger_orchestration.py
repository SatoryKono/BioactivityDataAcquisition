"""Internal orchestration helpers for ``MergeService``."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    import polars as pl

    from bioetl.application.composite.column_orderer import ColumnOrdererService
    from bioetl.application.composite.conflict_resolver import ConflictResolverService
    from bioetl.application.composite.join_planner import JoinPlannerService
    from bioetl.domain.composite.config import DependencyConfig, EnricherConfig
    from bioetl.domain.composite.cross_validation import CrossValidationStats
    from bioetl.domain.composite.result import (
        DependencyResult,
        EnrichmentResult,
        MergeResult,
    )
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class MergeInputContext:
    """Resolved seed, dependency, and enricher inputs for one merge run."""

    seed_df: pl.DataFrame
    records_from_seed: int
    effective_seed_pipeline: str | None
    sources_used: list[str]
    enricher_dfs: dict[str, pl.DataFrame]
    dependency_dfs: dict[str, pl.DataFrame]


@dataclass(frozen=True, slots=True)
class MergePostJoinContext:
    """Post-join merge state ready for persistence and result assembly."""

    merged_df: pl.DataFrame
    records_merged: int
    records_enriched: int
    cv_stats: CrossValidationStats | None
    quarantine_payloads: list[dict[str, object]]


class MergeWorkflowContext(Protocol):
    """Subset of MergeService API required by orchestration helpers."""

    _logger: LoggerPort
    _join_planner: JoinPlannerService
    _conflict_resolver: ConflictResolverService
    _orderer: ColumnOrdererService

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

    def _run_cross_validation(
        self,
        merged_df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        enricher_dfs: dict[str, pl.DataFrame],
        effective_seed_pipeline: str | None,
    ) -> tuple[pl.DataFrame, CrossValidationStats | None, list[dict[str, object]]]: ...

    def _add_lineage(
        self,
        df: pl.DataFrame,
        enrichment_results: dict[str, EnrichmentResult],
        run_id: str,
        sources_used: list[str],
        dependency_results: dict[str, DependencyResult] | None = None,
    ) -> pl.DataFrame: ...

    def _drop_excluded_fields(self, df: pl.DataFrame) -> pl.DataFrame: ...

    def _count_enriched_records(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> int: ...

    async def _write_outputs(
        self,
        df: pl.DataFrame,
        run_id: str,
        sources_used: list[str],
    ) -> None: ...

    def _build_merge_result(
        self,
        merged_df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        records_merged: int,
        records_from_seed: int,
        records_enriched: int,
        sources_used: list[str],
        duration_seconds: float,
        cv_stats: CrossValidationStats | None,
        quarantine_payloads: list[dict[str, object]],
    ) -> MergeResult: ...


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


def finalize_merged_dataframe(
    host: MergeWorkflowContext,
    *,
    merged_df: pl.DataFrame,
    enrichers: Sequence[EnricherConfig],
    enrichment_results: dict[str, EnrichmentResult],
    effective_seed_pipeline: str | None,
    run_id: str,
    sources_used: list[str],
    dependency_results: dict[str, DependencyResult] | None,
    enricher_dfs: dict[str, pl.DataFrame],
) -> pl.DataFrame:
    """Apply conflict resolution, lineage, exclusions, and final ordering."""
    merged_df = host._conflict_resolver.resolve_conflicts(
        df=merged_df,
        _enricher_dfs=enricher_dfs,
        enrichers=enrichers,
        seed_pipeline=effective_seed_pipeline,
    )
    merged_df = host._add_lineage(
        df=merged_df,
        enrichment_results=enrichment_results,
        run_id=run_id,
        sources_used=sources_used,
        dependency_results=dependency_results,
    )
    merged_df = host._drop_excluded_fields(merged_df)
    merged_df = host._orderer.order_columns(merged_df)
    host._logger.info(
        "Ordered columns by semantic groups",
        total_columns=len(merged_df.columns),
    )
    return merged_df


def finalize_post_join_context(
    host: MergeWorkflowContext,
    *,
    merged_df: pl.DataFrame,
    enrichers: Sequence[EnricherConfig],
    enrichment_results: dict[str, EnrichmentResult],
    effective_seed_pipeline: str | None,
    run_id: str,
    sources_used: list[str],
    dependency_results: dict[str, DependencyResult] | None,
    enricher_dfs: dict[str, pl.DataFrame],
) -> MergePostJoinContext:
    """Run post-join validation/finalization and derive merge result counters."""
    merged_df, cv_stats, quarantine_payloads = host._run_cross_validation(
        merged_df=merged_df,
        enrichers=enrichers,
        enricher_dfs=enricher_dfs,
        effective_seed_pipeline=effective_seed_pipeline,
    )
    merged_df = finalize_merged_dataframe(
        host,
        merged_df=merged_df,
        enrichers=enrichers,
        enrichment_results=enrichment_results,
        effective_seed_pipeline=effective_seed_pipeline,
        run_id=run_id,
        sources_used=sources_used,
        dependency_results=dependency_results,
        enricher_dfs=enricher_dfs,
    )
    records_merged = len(merged_df)
    records_enriched = host._count_enriched_records(
        merged_df,
        enrichers,
        effective_seed_pipeline,
    )
    return MergePostJoinContext(
        merged_df=merged_df,
        records_merged=records_merged,
        records_enriched=records_enriched,
        cv_stats=cv_stats,
        quarantine_payloads=quarantine_payloads,
    )


async def persist_and_build_result(
    host: MergeWorkflowContext,
    *,
    merged_df: pl.DataFrame,
    enrichers: Sequence[EnricherConfig],
    records_merged: int,
    records_from_seed: int,
    records_enriched: int,
    sources_used: list[str],
    cv_stats: CrossValidationStats | None,
    quarantine_payloads: list[dict[str, object]],
    run_id: str,
    started_at: datetime,
) -> MergeResult:
    """Persist merge outputs and build the domain ``MergeResult``."""
    await host._write_outputs(merged_df, run_id=run_id, sources_used=sources_used)
    completed_at = datetime.now(tz=UTC)
    duration = (completed_at - started_at).total_seconds()

    host._logger.info(
        "Merge completed",
        records_merged=records_merged,
        sources_used=sources_used,
        duration_seconds=duration,
    )
    return host._build_merge_result(
        merged_df=merged_df,
        enrichers=enrichers,
        records_merged=records_merged,
        records_from_seed=records_from_seed,
        records_enriched=records_enriched,
        sources_used=sources_used,
        duration_seconds=duration,
        cv_stats=cv_stats,
        quarantine_payloads=quarantine_payloads,
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
