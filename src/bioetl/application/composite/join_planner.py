"""Join planning and execution for composite merge pipeline."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.composite.join_execution import JoinHow
from bioetl.application.composite.join_planner_delegation_mixin import (
    JoinPlannerDelegationMixin,
)
from bioetl.application.composite.join_planner_helpers import (
    EnricherJoinMetadataContext,
    build_enricher_join_metadata,
    parse_pipeline_name,
    prepare_join_frames,
)
from bioetl.application.composite.protocols import (
    DependencyJoinerProtocol,
    JoinExecutorProtocol,
    JoinKeyResolverProtocol,
)

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.aggregator import EnricherAggregator
    from bioetl.application.composite.column_renamer import ColumnRenamer
    from bioetl.application.composite.conflict_resolver import ConflictResolverService
    from bioetl.application.composite.deduplication import EnricherDeduplicatorService
    from bioetl.domain.composite.config import (
        EnricherConfig,
        MergeConfig,
    )
    from bioetl.domain.ports import LoggerPort

__all__ = ["JoinHow", "JoinPlannerService"]


@dataclass(frozen=True, slots=True)
class _PreparedEnricherJoinContext:
    enricher_pipeline: str
    metadata: EnricherJoinMetadataContext
    merged_df: pl.DataFrame
    enricher_df: pl.DataFrame


class JoinPlannerService(JoinPlannerDelegationMixin):
    """Prepares and executes enricher/dependency joins with key normalization."""

    _NORMALIZE_JOIN_KEYS: frozenset[str] = frozenset({"doi", "pmid", "pmc_id"})
    _SYSTEM_COLUMNS_TO_DROP: frozenset[str] = frozenset(
        {
            "_run_id",
            "_run_type",
            "_source_batch_id",
            "_ingestion_ts",
            "_dq_warn",
            "_dq_error",
            "_index",
            "_lookup_method",
            "_original_id",
            "_source",
        }
    )

    _parse_pipeline_name = staticmethod(parse_pipeline_name)

    def __init__(
        self,
        merge_config: MergeConfig,
        logger: LoggerPort,
        deduplicator: EnricherDeduplicatorService,
        aggregator: EnricherAggregator,
        renamer: ColumnRenamer,
        conflict_resolver: ConflictResolverService,
        join_key_resolver: JoinKeyResolverProtocol,
        join_executor: JoinExecutorProtocol,
        dependency_joiner: DependencyJoinerProtocol,
        field_alias_resolver: Callable[[str], dict[str, str] | None],
    ) -> None:
        """Initialise the join planner with explicit collaborator services.

        Required collaborators (``deduplicator``, ``aggregator``, ``renamer``,
        ``conflict_resolver``, ``join_key_resolver``, ``join_executor``,
        ``dependency_joiner``) must be provided explicitly. See ADR-026 for the
        composite join workflow design.

        Args:
            merge_config: Domain merge configuration containing join strategy,
                enricher list, and column-conflict policy.
            logger: Structured logger forwarded to all collaborator services.
            deduplicator: Service that removes duplicate rows from enricher DataFrames
                before joining.
            aggregator: Service that performs many-to-one aggregation on enricher
                DataFrames when ``EnricherConfig.cardinality == MANY_TO_ONE``.
            renamer: Service that qualifies enricher column names to the
                ``{provider}.{entity}.{field}`` convention.
            conflict_resolver: Service that detects and resolves column-name conflicts
                between the seed/merged frame and an enricher frame.
            field_alias_resolver: Callable returning a field-alias mapping
                for a given pipeline name.
            join_key_resolver: ``JoinKeyResolverProtocol`` implementation for
                qualified/unqualified join-key resolution.
            join_executor: ``JoinExecutorProtocol`` implementation for Polars joins.
            dependency_joiner: ``DependencyJoinerProtocol`` implementation for
                dependency-specific join preparation and execution.
        """
        self._config = merge_config
        self._logger = logger
        self._deduplicator = deduplicator
        self._aggregator = aggregator
        self._renamer = renamer
        self._conflict_resolver = conflict_resolver
        self._field_alias_resolver = field_alias_resolver
        self._join_key_resolver = join_key_resolver
        self._join_executor = join_executor
        self._dependency_joiner = dependency_joiner

    async def apply_joins(
        self,
        seed_df: pl.DataFrame,
        enricher_dfs: dict[str, pl.DataFrame],
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Join successful enrichers to seed DataFrame.

        Args:
            seed_df: Base seed DataFrame to join enrichers into.
            enricher_dfs: Mapping from pipeline name to loaded enricher DataFrame.
            enrichers: Ordered enricher configurations defining join logic.
            seed_pipeline: Optional seed pipeline name for qualified key resolution.

        Returns:
            Merged DataFrame with all available enricher data joined to the seed frame.
        """
        merged = seed_df
        for enricher in enrichers:
            enricher_df = enricher_dfs.get(enricher.pipeline)
            if enricher_df is None:
                continue

            merged = self._merge_single_enricher(
                merged_df=merged,
                enricher_df=enricher_df,
                enricher=enricher,
                seed_pipeline=seed_pipeline,
            )
        return merged

    def _merge_single_enricher(
        self,
        *,
        merged_df: pl.DataFrame,
        enricher_df: pl.DataFrame,
        enricher: EnricherConfig,
        seed_pipeline: str | None,
    ) -> pl.DataFrame:
        return self._execute_prepared_enricher_join(
            prepared_context=self._prepare_enricher_join_context(
                merged_df=merged_df,
                enricher_df=enricher_df,
                enricher=enricher,
                seed_pipeline=seed_pipeline,
            ),
        )

    def _prepare_enricher_join_context(
        self,
        *,
        merged_df: pl.DataFrame,
        enricher_df: pl.DataFrame,
        enricher: EnricherConfig,
        seed_pipeline: str | None,
    ) -> _PreparedEnricherJoinContext:
        metadata = build_enricher_join_metadata(
            join_keys=enricher.join_keys,
            primary_join_key=enricher.primary_join_key,
            enricher_pipeline=enricher.pipeline,
            seed_pipeline=seed_pipeline,
            merged_columns=merged_df.columns,
            resolve_join_key_names=self.resolve_join_key_names,
        )
        prepared_enricher_df = self._prepare_enricher_dataframe(
            enricher_df=enricher_df,
            enricher=enricher,
        )
        merged_df, prepared_enricher_df = self._prepare_join_frames_for_enricher(
            merged_df=merged_df,
            prepared_enricher_df=prepared_enricher_df,
            metadata=metadata,
            enricher_pipeline=enricher.pipeline,
            seed_pipeline=seed_pipeline,
        )
        return _PreparedEnricherJoinContext(
            enricher_pipeline=enricher.pipeline,
            metadata=metadata,
            merged_df=merged_df,
            enricher_df=prepared_enricher_df,
        )

    def _execute_prepared_enricher_join(
        self,
        *,
        prepared_context: _PreparedEnricherJoinContext,
    ) -> pl.DataFrame:
        resolved_merged_df, resolved_enricher_df = self._resolve_pre_join_conflicts(
            merged_df=prepared_context.merged_df,
            enricher_df=prepared_context.enricher_df,
            join_key_set=prepared_context.metadata.join_key_set,
        )
        return self.execute_polars_join(
            resolved_merged_df,
            resolved_enricher_df,
            prepared_context.metadata.seed_join_key,
            prepared_context.metadata.enricher_join_key,
            prepared_context.enricher_pipeline,
        )

    def _prepare_join_frames_for_enricher(
        self,
        *,
        merged_df: pl.DataFrame,
        prepared_enricher_df: pl.DataFrame,
        metadata: EnricherJoinMetadataContext,
        enricher_pipeline: str,
        seed_pipeline: str | None,
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Prepare normalized/qualified left-right frames for join execution."""
        return prepare_join_frames(
            merged_df=merged_df,
            right_df=prepared_enricher_df,
            left_join_keys=metadata.join_keys_list,
            right_join_keys=metadata.join_keys_list,
            right_pipeline=enricher_pipeline,
            seed_pipeline=seed_pipeline,
            deduplicator=self._deduplicator,
            join_key_resolver=self._join_key_resolver,
            renamer=self._renamer,
            logger=self._logger,
            field_alias_resolver=self._field_alias_resolver,
            drop_system_columns=self.drop_system_columns,
            log_message="Renamed enricher columns to qualified format",
            log_field_name="enricher",
        )

    def _resolve_pre_join_conflicts(
        self,
        *,
        merged_df: pl.DataFrame,
        enricher_df: pl.DataFrame,
        join_key_set: set[str],
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Resolve technical column-name conflicts before join execution."""
        return self._conflict_resolver.detect_and_resolve_conflicts(
            merged_df,
            enricher_df,
            join_key_set,
        )

    def _prepare_enricher_dataframe(
        self,
        *,
        enricher_df: pl.DataFrame,
        enricher: EnricherConfig,
    ) -> pl.DataFrame:
        if enricher.is_many_to_one and enricher.aggregation is not None:
            return self._aggregator.aggregate(
                enricher_df,
                enricher.aggregation,
                enricher.pipeline,
            )
        return enricher_df
