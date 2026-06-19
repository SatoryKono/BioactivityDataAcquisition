"""Post-join finalization helpers for ``MergeService`` orchestration."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import polars as pl

from bioetl.application.composite.column_service import ColumnOrderService
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.runtime_timestamps import derive_completion_timestamp
from bioetl.domain.composite.config_models import EnricherConfig
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
        metadata_timestamp=metadata_timestamp,
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
    host: MergePostJoinWorkflowContext,
    *,
    merged_df: pl.DataFrame,
    enrichers: Sequence[EnricherConfig],
    records_merged: int,
    records_from_seed: int,
    records_enriched: int,
    sources_used: list[str],
    cv_stats: CrossValidationStats | None,
    quarantine_payloads: list[dict[str, object]],
    metadata_timestamp: datetime | None,
    run_id: str,
    started_at: datetime,
    started_monotonic: float,
) -> MergeResult:
    """Persist merge outputs and build the domain ``MergeResult``."""
    await host._write_outputs(
        merged_df,
        metadata_timestamp=metadata_timestamp,
        run_id=run_id,
        sources_used=sources_used,
    )
    _, duration = derive_completion_timestamp(
        started_at=started_at,
        started_monotonic=started_monotonic,
    )

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
