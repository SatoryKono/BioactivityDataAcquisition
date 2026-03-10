"""Merge Service for composite pipelines. See ADR-026."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from bioetl.application.clock import DefaultClock
from bioetl.application.composite.aggregator import EnricherAggregatorService
from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.application.composite.column_orderer import ColumnOrdererService
from bioetl.application.composite.column_priority_orderer import (
    ColumnPriorityOrdererService,
)
from bioetl.application.composite.column_renamer import ColumnRenamerService
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.deduplication import EnricherDeduplicatorService
from bioetl.application.composite.join_planner import JoinPlannerService
from bioetl.application.composite.merger_compat_mixin import MergeCompatibilityHelper
from bioetl.application.composite.merger_io_mixin import MergeIOHelper
from bioetl.application.composite.merger_metrics_mixin import MergeMetricsHelper
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    MergeResult,
)

if TYPE_CHECKING:
    from bioetl.application.composite.cross_validator import (
        EnrichmentCrossValidationService,
    )
    from bioetl.domain.composite.config import (
        DependencyConfig,
        EnricherConfig,
        MergeConfig,
    )
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.ports import ClockPort, DeltaReaderPort, LoggerPort, StoragePort


def _path_to_table_name(path: str) -> str:
    """Convert a full path to a table name by stripping layer prefix."""
    normalized = path.replace("\\", "/")

    for layer in ("silver/", "gold/", "bronze/"):
        if layer in normalized:
            idx = normalized.find(layer)
            return normalized[idx + len(layer) :]

    return path


class MergeService(MergeIOHelper, MergeCompatibilityHelper, MergeMetricsHelper):
    """Facade/orchestrator for seed+dependency+enricher merge workflow."""

    def __init__(
        self,
        merge_config: MergeConfig,
        storage: StoragePort,
        logger: LoggerPort,
        clock: ClockPort | None = None,
        delta_reader: DeltaReaderPort | None = None,
        field_group_registry: FieldGroupRegistry | None = None,
        cross_validator: EnrichmentCrossValidationService | None = None,
        gold_schema: Any | None = None,  # Any: Pandera DataFrameModel class or instance
        *,
        deduplicator: EnricherDeduplicatorService | None = None,
        aggregator: EnricherAggregatorService | None = None,
        renamer: ColumnRenamerService | None = None,
        orderer: ColumnOrdererService | None = None,
        priority_orderer: ColumnPriorityOrdererService | None = None,
        coalesce_policy: CoalescePolicyService | None = None,
        conflict_resolver: ConflictResolverService | None = None,
        join_planner: JoinPlannerService | None = None,
    ) -> None:
        self._config = merge_config
        self._storage = storage
        self._logger = logger
        self._clock = clock or DefaultClock()
        self._delta_reader = delta_reader
        self._field_group_registry = field_group_registry
        self._cross_validator = cross_validator
        self._gold_schema = gold_schema

        self._deduplicator = deduplicator or EnricherDeduplicatorService(logger)
        self._aggregator = aggregator or EnricherAggregatorService(logger)
        self._renamer = renamer or ColumnRenamerService(logger)
        self._orderer = orderer or ColumnOrdererService(
            logger,
            column_groups=merge_config.column_groups
            if merge_config.column_groups
            else None,
        )

        self._priority_orderer = priority_orderer or ColumnPriorityOrdererService(
            logger
        )
        self._coalesce_policy = coalesce_policy or CoalescePolicyService(
            logger,
            self._priority_orderer,
        )
        self._conflict_resolver = conflict_resolver or ConflictResolverService(
            merge_config,
            logger,
            self._coalesce_policy,
        )
        self._join_planner = join_planner or JoinPlannerService(
            merge_config=merge_config,
            logger=logger,
            deduplicator=self._deduplicator,
            aggregator=self._aggregator,
            renamer=self._renamer,
            conflict_resolver=self._conflict_resolver,
            field_alias_resolver=self._get_field_aliases,
        )

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
        """Merge seed, dependency, and enricher data into unified output."""
        started_at = self._clock.now_utc()

        (
            seed_df,
            records_from_seed,
            effective_seed_pipeline,
        ) = await self._prepare_seed_dataframe(
            seed_table,
            seed_pipeline,
        )

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

        records_merged = len(merged_df)
        records_enriched = self._count_enriched_records(
            merged_df,
            enrichers,
            effective_seed_pipeline,
        )

        await self._write_outputs(merged_df, run_id=run_id, sources_used=sources_used)

        completed_at = self._clock.now_utc()
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
