"""Join planning and execution for composite merge pipeline."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.composite.join_execution import JoinHow
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
        DependencyConfig,
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


class JoinPlannerService:
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

    def find_join_key_column(
        self,
        key: str,
        columns: list[str],
        pipeline: str | None = None,
    ) -> str | None:
        """Find a join key column, preferring qualified names when available."""
        return self._join_key_resolver.find_join_key_column(key, columns, pipeline)

    def normalize_join_key_columns(
        self,
        df: pl.DataFrame,
        join_keys: list[str],
        pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Normalize selected identifier join keys to lowercase."""
        return self._join_key_resolver.normalize_join_key_columns(
            df,
            join_keys,
            pipeline,
        )

    def drop_system_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Drop system columns that should not leak from the right side."""
        return self._dependency_joiner.drop_system_columns(df)

    def execute_polars_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_key: str,
        right_key: str,
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Execute a single-key join while preserving the right join key."""
        return self._join_executor.execute_polars_join(
            left_df,
            right_df,
            left_key,
            right_key,
            pipeline_name,
        )

    def resolve_join_key_names(
        self,
        primary_key: str,
        seed_pipeline: str | None,
        enricher_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, str | None]:
        """Resolve qualified join key names for a seed/enricher join."""
        return self._join_key_resolver.resolve_join_key_names(
            primary_key,
            seed_pipeline,
            enricher_pipeline,
            merged_columns,
        )

    def resolve_join_key_names_asymmetric(
        self,
        left_key: str,
        right_key: str,
        left_pipeline: str | None,
        right_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, str | None]:
        """Resolve qualified join key names when left/right keys differ."""
        return self._join_key_resolver.resolve_join_key_names_asymmetric(
            left_key,
            right_key,
            left_pipeline,
            right_pipeline,
            merged_columns,
        )

    def resolve_composite_join_keys(
        self,
        join_keys_list: list[str],
        left_pipeline: str | None,
        right_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[list[str], list[str], set[str]]:
        """Resolve all keys required for a composite-key dependency join."""
        return self._join_key_resolver.resolve_composite_join_keys(
            join_keys_list,
            left_pipeline,
            right_pipeline,
            merged_columns,
        )

    def execute_composite_key_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_keys: list[str],
        right_keys: list[str],
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Execute a multi-key join preserving right-side key columns."""
        return self._join_executor.execute_composite_key_join(
            left_df,
            right_df,
            left_keys,
            right_keys,
            pipeline_name,
        )

    def get_polars_join_type(self) -> JoinHow:
        """Map the configured merge strategy to a Polars join type."""
        return self._join_executor.get_polars_join_type()

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
        merged_df, prepared_enricher_df = prepare_join_frames(
            merged_df=merged_df,
            right_df=prepared_enricher_df,
            left_join_keys=metadata.join_keys_list,
            right_join_keys=metadata.join_keys_list,
            right_pipeline=enricher.pipeline,
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
        resolved_merged_df, resolved_enricher_df = (
            self._conflict_resolver.detect_and_resolve_conflicts(
                prepared_context.merged_df,
                prepared_context.enricher_df,
                prepared_context.metadata.join_key_set,
            )
        )
        return self.execute_polars_join(
            resolved_merged_df,
            resolved_enricher_df,
            prepared_context.metadata.seed_join_key,
            prepared_context.metadata.enricher_join_key,
            prepared_context.enricher_pipeline,
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

    async def apply_dependency_joins(
        self,
        merged_df: pl.DataFrame,
        dependency_dfs: dict[str, pl.DataFrame],
        dependencies: Sequence[DependencyConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply configured dependency joins to merged DataFrame.

        Args:
            merged_df: Current merged DataFrame to join dependencies into.
            dependency_dfs: Mapping from pipeline name to loaded dependency DataFrame.
            dependencies: Dependency configurations defining join logic.
            seed_pipeline: Optional seed pipeline name for qualified key resolution.

        Returns:
            DataFrame with all configured dependency tables joined to the merged frame.
        """
        return self._dependency_joiner.apply_dependency_joins(
            merged_df=merged_df,
            dependency_dfs=dependency_dfs,
            dependencies=dependencies,
            seed_pipeline=seed_pipeline,
        )

    def apply_composite_key_dependency_join(
        self,
        merged_df: pl.DataFrame,
        dep_df: pl.DataFrame,
        dep: DependencyConfig,
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Join dependency using all configured composite join keys.

        Args:
            merged_df: Current merged DataFrame to join the dependency into.
            dep_df: Dependency DataFrame to join.
            dep: Dependency configuration specifying join keys and pipeline.
            seed_pipeline: Optional seed pipeline name for left-side key resolution.

        Returns:
            DataFrame with the dependency table joined using all configured join keys.
        """
        return self._dependency_joiner.apply_composite_key_dependency_join(
            merged_df=merged_df,
            dep_df=dep_df,
            dep=dep,
            seed_pipeline=seed_pipeline,
        )
