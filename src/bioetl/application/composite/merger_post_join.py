"""Post-join finalization helpers for ``MergeService`` orchestration."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import polars as pl

from bioetl.application.composite.column_service import ColumnOrderService
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.helpers.target_classification_stage import (
    CompositeTargetClassification,
    apply_joined_classification,
)
from bioetl.domain.composite import EnricherConfig
from bioetl.domain.composite.cross_validation import CrossValidationStats
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    MergeResult,
)
from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class MergePostJoinContext:
    """Post-join merge state ready for persistence and result assembly."""

    merged_df: pl.DataFrame
    records_merged: int
    records_enriched: int
    cv_stats: CrossValidationStats | None
    quarantine_payloads: list[dict[str, object]]


class MergePostJoinWorkflowContext(Protocol):
    """Subset of ``MergeService`` API required by post-join helpers."""

    _logger: LoggerPort
    _conflict_resolver: ConflictResolverService
    _order_service: ColumnOrderService | None

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
        metadata_timestamp: datetime | None,
        sources_used: list[str],
        dependency_results: dict[str, DependencyResult] | None = None,
    ) -> pl.DataFrame: ...

    def _drop_excluded_fields(self, df: pl.DataFrame) -> pl.DataFrame: ...

    def _apply_field_mappings(self, df: pl.DataFrame) -> pl.DataFrame: ...

    def _count_enriched_records(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> int: ...

    async def _write_outputs(
        self,
        df: pl.DataFrame,
        metadata_timestamp: datetime | None,
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


def finalize_merged_dataframe(
    host: MergePostJoinWorkflowContext,
    *,
    merged_df: pl.DataFrame,
    enrichers: Sequence[EnricherConfig],
    enrichment_results: dict[str, EnrichmentResult],
    effective_seed_pipeline: str | None,
    run_id: str,
    metadata_timestamp: datetime | None,
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
    merged_df = host._apply_field_mappings(merged_df)
    merged_df = host._add_lineage(
        df=merged_df,
        enrichment_results=enrichment_results,
        run_id=run_id,
        metadata_timestamp=metadata_timestamp,
        sources_used=sources_used,
        dependency_results=dependency_results,
    )
    merged_df = host._drop_excluded_fields(merged_df)
    order_service = host._order_service
    if order_service is not None:
        merged_df = order_service.order_columns(merged_df)
        host._logger.info(
            "Ordered columns by semantic groups",
            total_columns=len(merged_df.columns),
        )
    return merged_df


def _bound_classification_stage(
    host: object,
) -> CompositeTargetClassification | None:
    stage = getattr(host, "_target_classification_stage", None)
    if isinstance(stage, CompositeTargetClassification):
        return stage
    return None


def finalize_post_join_context(
    host: MergePostJoinWorkflowContext,
    *,
    merged_df: pl.DataFrame,
    enrichers: Sequence[EnricherConfig],
    enrichment_results: dict[str, EnrichmentResult],
    effective_seed_pipeline: str | None,
    run_id: str,
    metadata_timestamp: datetime | None,
    sources_used: list[str],
    dependency_results: dict[str, DependencyResult] | None,
    enricher_dfs: dict[str, pl.DataFrame],
    dependency_dfs: dict[str, pl.DataFrame] | None = None,
    classification_started_at: datetime | None = None,
) -> MergePostJoinContext:
    """Run post-join validation/finalization and derive merge result counters."""
    merged_df, cv_stats, quarantine_payloads = host._run_cross_validation(
        merged_df=merged_df,
        enrichers=enrichers,
        enricher_dfs=enricher_dfs,
        effective_seed_pipeline=effective_seed_pipeline,
    )
    stage = _bound_classification_stage(host)
    ready = False
    try:
        merged_df = apply_joined_classification(
            stage,
            merged_df,
            run_id=run_id,
            started_at=classification_started_at or metadata_timestamp,
            dependency_frames=dependency_dfs,
        )
        merged_df = finalize_merged_dataframe(
            host,
            merged_df=merged_df,
            enrichers=enrichers,
            enrichment_results=enrichment_results,
            effective_seed_pipeline=effective_seed_pipeline,
            run_id=run_id,
            metadata_timestamp=metadata_timestamp,
            sources_used=sources_used,
            dependency_results=dependency_results,
            enricher_dfs=enricher_dfs,
        )
        if stage is not None:
            merged_df = stage.seal_decision(merged_df)
            merged_df = stage.refresh_content_hash(merged_df)
        records_merged = len(merged_df)
        records_enriched = host._count_enriched_records(
            merged_df,
            enrichers,
            effective_seed_pipeline,
        )
        context = MergePostJoinContext(
            merged_df=merged_df,
            records_merged=records_merged,
            records_enriched=records_enriched,
            cv_stats=cv_stats,
            quarantine_payloads=quarantine_payloads,
        )
        ready = True
        return context
    finally:
        if not ready and stage is not None:
            stage.abandon(run_id)
