"""Merge Service for composite pipelines. See ADR-026."""

from __future__ import annotations

__all__ = ["MergeService"]

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from bioetl.application.composite.merger_compat_mixin import MergeCompatibilityMixin
from bioetl.application.composite.merger_io_mixin import MergeIOMixin
from bioetl.application.composite.merger_metrics_mixin import MergeMetricsRecorderMixin
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    MergeResult,
)

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.aggregator import EnricherAggregatorService
    from bioetl.application.composite.coalesce_policy import CoalescePolicyService
    from bioetl.application.composite.column_orderer import ColumnOrdererService
    from bioetl.application.composite.column_priority_orderer import (
        ColumnPriorityOrdererService,
    )
    from bioetl.application.composite.column_renamer import ColumnRenamerService
    from bioetl.application.composite.conflict_resolver import ConflictResolverService
    from bioetl.application.composite.cross_validator import (
        EnrichmentCrossValidationService,
    )
    from bioetl.application.composite.deduplication import EnricherDeduplicatorService
    from bioetl.application.composite.join_planner import JoinPlannerService
    from bioetl.domain.composite.config import (
        DependencyConfig,
        EnricherConfig,
        MergeConfig,
    )
    from bioetl.domain.composite.cross_validation import CrossValidationStats
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.ports import DeltaReaderPort, LoggerPort, StoragePort


def _path_to_table_name(path: str) -> str:
    """Convert a full path to a table name by stripping layer prefix."""
    normalized = path.replace("\\", "/")

    for layer in ("silver/", "gold/", "bronze/"):
        if layer in normalized:
            idx = normalized.find(layer)
            return normalized[idx + len(layer) :]

    return path


class MergeService(MergeIOMixin, MergeCompatibilityMixin, MergeMetricsRecorderMixin):
    """Facade/orchestrator for seed+dependency+enricher merge workflow."""

    def __init__(
        self,
        merge_config: MergeConfig,
        storage: StoragePort,
        logger: LoggerPort,
        delta_reader: DeltaReaderPort | None = None,
        field_group_registry: FieldGroupRegistry | None = None,
        cross_validator: EnrichmentCrossValidationService | None = None,
        gold_schema: Any | None = None,  # Any: Pandera DataFrameModel class or instance
        *,
        deduplicator: EnricherDeduplicatorService,
        aggregator: EnricherAggregatorService,
        renamer: ColumnRenamerService,
        orderer: ColumnOrdererService,
        priority_orderer: ColumnPriorityOrdererService,
        coalesce_policy: CoalescePolicyService,
        conflict_resolver: ConflictResolverService,
        join_planner: JoinPlannerService,
    ) -> None:
        """Initialise the MergeService with all required and optional collaborators.

        The ``MergeService`` acts as the central facade for the seed + enricher +
        dependency merge workflow described in ADR-026. All data-access and processing
        concerns are delegated to the injected collaborator services; this class is
        responsible only for orchestration and sequencing.

        Args:
            merge_config: Domain merge configuration (strategy, enricher list, column
                conflict policy, cross-validation settings).
            storage: ``StoragePort`` adapter used to persist merged Silver/Gold output.
            logger: Structured logger for progress and diagnostic output.
            delta_reader: Optional ``DeltaReaderPort`` for reading seed and enricher
                Silver tables; when ``None`` the service falls back to
                storage-based reads.
            field_group_registry: Optional registry mapping publication field names to
                semantic groups; enables Gold-layer column filtering and ordering.
            cross_validator: Optional service that validates consistency across
                enricher data sources after joining; ``None`` disables cross-validation.
            gold_schema: Optional Pandera ``DataFrameModel`` class used to validate
                the Gold-layer output schema; type is ``Any`` because it is a class
                reference rather than an instance.
            deduplicator: Service that removes duplicate rows from enricher DataFrames
                keyed on join fields.
            aggregator: Service that aggregates many-to-one enricher DataFrames before
                joining.
            renamer: Service that qualifies column names to the
                ``{provider}.{entity}.{field}`` convention.
            orderer: Service that applies semantic group-based column ordering to the
                merged output.
            priority_orderer: Service that resolves provider priority ordering for
                coalesced columns.
            coalesce_policy: Service that selects the winning value for columns
                present in multiple enrichers.
            conflict_resolver: Service that detects and resolves column-name conflicts
                between the seed frame and enricher frames.
            join_planner: Pre-wired service that executes enricher and dependency
                joins against the seed DataFrame.
        """
        self._config = merge_config
        self._storage = storage
        self._logger = logger
        self._delta_reader = delta_reader
        self._field_group_registry = field_group_registry
        self._cross_validator = cross_validator
        self._gold_schema = gold_schema

        self._deduplicator = deduplicator
        self._aggregator = aggregator
        self._renamer = renamer
        self._orderer = orderer
        self._priority_orderer = priority_orderer
        self._coalesce_policy = coalesce_policy
        self._conflict_resolver = conflict_resolver
        self._join_planner = join_planner

    async def merge(
        self,
        seed_table: str,
        enrichers: Sequence[EnricherConfig],
        enrichment_results: dict[str, EnrichmentResult],
        run_id: str,
        seed_pipeline: str | None = None,
        dependencies: Sequence[DependencyConfig] | None = None,
        dependency_results: dict[str, DependencyResult] | None = None,
    ) -> MergeResult:
        """Merge seed, dependency, and enricher data into unified output.

        Returns:
            MergeResult with merged record counts, source provenance, cross-validation
            stats, quarantine payloads, and duration metrics.
        """
        started_at = datetime.now(tz=UTC)
        (
            seed_df,
            records_from_seed,
            effective_seed_pipeline,
            sources_used,
            enricher_dfs,
            dependency_dfs,
        ) = await self._load_merge_inputs(
            seed_table=seed_table,
            seed_pipeline=seed_pipeline,
            enrichers=enrichers,
            enrichment_results=enrichment_results,
            dependencies=dependencies,
            dependency_results=dependency_results,
        )

        merged_df = await self._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs=enricher_dfs,
            enrichers=enrichers,
            seed_pipeline=effective_seed_pipeline,
        )

        merged_df = await self._apply_dependency_joins_if_needed(
            merged_df=merged_df,
            dependency_dfs=dependency_dfs,
            dependencies=dependencies,
            seed_pipeline=effective_seed_pipeline,
        )

        merged_df, cv_stats, quarantine_payloads = self._run_cross_validation(
            merged_df=merged_df,
            enrichers=enrichers,
            enricher_dfs=enricher_dfs,
            effective_seed_pipeline=effective_seed_pipeline,
        )

        merged_df = self._finalize_merged_dataframe(
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
        records_enriched = self._count_enriched_records(
            merged_df,
            enrichers,
            effective_seed_pipeline,
        )
        return await self._persist_and_build_result(
            merged_df=merged_df,
            enrichers=enrichers,
            records_merged=records_merged,
            records_from_seed=records_from_seed,
            records_enriched=records_enriched,
            sources_used=sources_used,
            cv_stats=cv_stats,
            quarantine_payloads=quarantine_payloads,
            run_id=run_id,
            started_at=started_at,
        )

    async def _load_merge_inputs(
        self,
        *,
        seed_table: str,
        seed_pipeline: str | None,
        enrichers: Sequence[EnricherConfig],
        enrichment_results: dict[str, EnrichmentResult],
        dependencies: Sequence[DependencyConfig] | None,
        dependency_results: dict[str, DependencyResult] | None,
    ) -> tuple[
        pl.DataFrame,
        int,
        str | None,
        list[str],
        dict[str, pl.DataFrame],
        dict[str, pl.DataFrame],
    ]:
        """Load seed, enricher and dependency frames for merge orchestration."""
        (
            seed_df,
            records_from_seed,
            effective_seed_pipeline,
        ) = await self._prepare_seed_dataframe(seed_table, seed_pipeline)
        sources_used = ["seed"]

        enricher_dfs, enricher_sources = await self._load_enricher_dataframes(
            enrichers,
            enrichment_results,
        )
        sources_used.extend(enricher_sources)

        dependency_dfs, dependency_sources = await self._load_dependency_dataframes(
            dependencies,
            dependency_results,
        )
        sources_used.extend(dependency_sources)
        return (
            seed_df,
            records_from_seed,
            effective_seed_pipeline,
            sources_used,
            enricher_dfs,
            dependency_dfs,
        )

    def _finalize_merged_dataframe(
        self,
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
        """Apply conflict resolution, lineage and final column ordering."""
        merged_df = self._conflict_resolver.resolve_conflicts(
            df=merged_df,
            _enricher_dfs=enricher_dfs,
            enrichers=enrichers,
            seed_pipeline=effective_seed_pipeline,
        )
        merged_df = self._add_lineage(
            df=merged_df,
            enrichment_results=enrichment_results,
            run_id=run_id,
            sources_used=sources_used,
            dependency_results=dependency_results,
        )
        merged_df = self._drop_excluded_fields(merged_df)
        merged_df = self._orderer.order_columns(merged_df)
        self._logger.info(
            "Ordered columns by semantic groups",
            total_columns=len(merged_df.columns),
        )
        return merged_df

    async def _persist_and_build_result(
        self,
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
        """Persist merge outputs and construct final domain result."""
        await self._write_outputs(merged_df, run_id=run_id, sources_used=sources_used)
        completed_at = datetime.now(tz=UTC)
        duration = (completed_at - started_at).total_seconds()

        self._logger.info(
            "Merge completed",
            records_merged=records_merged,
            sources_used=sources_used,
            duration_seconds=duration,
        )
        return self._build_merge_result(
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
