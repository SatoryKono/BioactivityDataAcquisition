"""Internal orchestration helpers for ``MergeService``."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from bioetl.application.composite.merger_orchestration_types import (
    MergeExecutionContext,
    MergeExecutionRequest,
    MergeExecutionRequestSpec,
    MergeInputContext,
    MergeWorkflowContext,
)
from bioetl.application.composite.merger_post_join import (
    finalize_post_join_context,
    persist_and_build_result,
)
from bioetl.application.runtime_timestamps import capture_runtime_timing_anchor

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.domain.composite import DependencyConfig, EnricherConfig
    from bioetl.domain.composite.result import (
        DependencyResult,
        EnrichmentResult,
        MergeResult,
    )

__all__ = [
    "MergeExecutionContext",
    "MergeExecutionRequest",
    "MergeExecutionRequestSpec",
    "MergeInputContext",
    "MergeWorkflowContext",
    "build_merge_execution_request",
    "execute_merge_execution_core",
    "execute_merge_request",
    "execute_merge_workflow",
    "load_merge_inputs",
    "prepare_merge_execution_context",
    "resolve_merge_metadata_timestamp",
]


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
    prepared_seed = await host._prepare_seed_dataframe(seed_table, seed_pipeline)
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
        seed_df=prepared_seed.seed_df,
        records_from_seed=prepared_seed.records_from_seed,
        effective_seed_pipeline=prepared_seed.effective_seed_pipeline,
        sources_used=sources_used,
        enricher_dfs=enricher_dfs,
        dependency_dfs=dependency_dfs,
    )


def resolve_merge_metadata_timestamp(
    cached_bronze_date: object | None,
) -> datetime | None:
    """Return deterministic replay timestamp from cached bronze date."""
    if cached_bronze_date is None:
        return None
    replay_date = date.fromisoformat(str(cached_bronze_date))
    return datetime.combine(replay_date, datetime.min.time(), tzinfo=UTC)


def build_merge_execution_request(
    *,
    seed_table: str,
    enrichers: Sequence[EnricherConfig],
    enrichment_results: dict[str, EnrichmentResult],
    run_id: str,
    metadata_timestamp: datetime | None = None,
    seed_pipeline: str | None = None,
    dependencies: Sequence[DependencyConfig] | None = None,
    dependency_results: dict[str, DependencyResult] | None = None,
) -> MergeExecutionRequest:
    """Build the canonical request envelope for merge/join execution."""
    return MergeExecutionRequestSpec(
        seed_table=seed_table,
        seed_pipeline=seed_pipeline,
        enrichers=enrichers,
        enrichment_results=enrichment_results,
        run_id=run_id,
        metadata_timestamp=metadata_timestamp,
        dependencies=dependencies,
        dependency_results=dependency_results,
    )


async def prepare_merge_execution_context(
    host: MergeWorkflowContext,
    request: MergeExecutionRequestSpec,
) -> MergeExecutionContext:
    """Load all merge inputs and bind them to one execution context model."""
    started_at, started_monotonic = capture_runtime_timing_anchor(clock=host._clock)
    return MergeExecutionContext(
        request=request,
        started_at=started_at,
        started_monotonic=started_monotonic,
        loaded_inputs=await load_merge_inputs(
            host,
            seed_table=request.seed_table,
            seed_pipeline=request.seed_pipeline,
            enrichers=request.enrichers,
            enrichment_results=request.enrichment_results,
            dependencies=request.dependencies,
            dependency_results=request.dependency_results,
        ),
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
    request = build_merge_execution_request(
        seed_table=seed_table,
        enrichers=enrichers,
        enrichment_results=enrichment_results,
        run_id=run_id,
        seed_pipeline=seed_pipeline,
        dependencies=dependencies,
        dependency_results=dependency_results,
    )
    return await execute_merge_request(host, request)


async def execute_merge_execution_core(
    host: MergeWorkflowContext,
    execution_context: MergeExecutionContext,
) -> MergeResult:
    """Execute merge/join sequencing from one prepared execution context."""
    request = execution_context.request
    loaded = execution_context.loaded_inputs

    merged_df = await host._join_planner.apply_joins(
        seed_df=loaded.seed_df,
        enricher_dfs=loaded.enricher_dfs,
        enrichers=request.enrichers,
        seed_pipeline=loaded.effective_seed_pipeline,
    )
    merged_df = await host._apply_dependency_joins_if_needed(
        merged_df=merged_df,
        dependency_dfs=loaded.dependency_dfs,
        dependencies=request.dependencies,
        seed_pipeline=loaded.effective_seed_pipeline,
    )
    post_join_context = finalize_post_join_context(
        host,
        merged_df=merged_df,
        enrichers=request.enrichers,
        enrichment_results=request.enrichment_results,
        effective_seed_pipeline=loaded.effective_seed_pipeline,
        run_id=request.run_id,
        metadata_timestamp=request.metadata_timestamp,
        sources_used=loaded.sources_used,
        dependency_results=request.dependency_results,
        enricher_dfs=loaded.enricher_dfs,
    )
    return await persist_and_build_result(
        host,
        merged_df=post_join_context.merged_df,
        enrichers=request.enrichers,
        records_merged=post_join_context.records_merged,
        records_from_seed=loaded.records_from_seed,
        records_enriched=post_join_context.records_enriched,
        sources_used=loaded.sources_used,
        cv_stats=post_join_context.cv_stats,
        quarantine_payloads=post_join_context.quarantine_payloads,
        metadata_timestamp=request.metadata_timestamp,
        run_id=request.run_id,
        started_at=execution_context.started_at,
        started_monotonic=execution_context.started_monotonic,
    )


async def execute_merge_request(
    host: MergeWorkflowContext,
    request: MergeExecutionRequestSpec,
) -> MergeResult:
    """Execute the full composite merge workflow from a canonical request."""
    execution_context = await prepare_merge_execution_context(host, request)
    return await execute_merge_execution_core(host, execution_context)
