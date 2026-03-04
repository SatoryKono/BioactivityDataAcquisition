"""Join planning and execution for composite merge pipeline."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from bioetl.application.composite.dependency_joiner import DependencyJoinerService
from bioetl.application.composite.join_execution import JoinExecutorService, JoinHow
from bioetl.application.composite.join_key_resolution import JoinKeyResolverService
from bioetl.application.composite.join_planner_helpers import (
    parse_pipeline_name,
    resolve_field_aliases_from_registry,
)
from bioetl.application.composite.protocols import (
    DependencyJoinerProtocol,
    JoinExecutorProtocol,
    JoinKeyResolverProtocol,
)
from bioetl.domain.composite.strategy import MergeStrategy

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.aggregator import EnricherAggregatorService
    from bioetl.application.composite.column_renamer import ColumnRenamerService
    from bioetl.application.composite.conflict_resolver import ConflictResolverService
    from bioetl.application.composite.deduplication import EnricherDeduplicatorService
    from bioetl.domain.composite.config import (
        DependencyConfig,
        EnricherConfig,
        MergeConfig,
    )
    from bioetl.domain.ports import LoggerPort


__all__ = ["JoinHow", "JoinPlannerService"]


class JoinPlannerCompatibilityMixin:
    """Backward-compatible delegation helpers for join orchestration."""

    _config: MergeConfig
    _join_key_resolver: JoinKeyResolverProtocol
    _join_executor: JoinExecutorProtocol
    _dependency_joiner: DependencyJoinerProtocol

    def find_join_key_column(
        self,
        key: str,
        columns: list[str],
        pipeline: str | None = None,
    ) -> str | None:
        """Find key column name (qualified preferred, fallback unqualified)."""
        return self._join_key_resolver.find_join_key_column(key, columns, pipeline)

    def normalize_join_key_columns(
        self,
        df: pl.DataFrame,
        join_keys: list[str],
        pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Normalize selected identifier join key columns to lowercase."""
        return self._join_key_resolver.normalize_join_key_columns(
            df,
            join_keys,
            pipeline,
        )

    def drop_system_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Drop system columns that must come only from seed."""
        return self._dependency_joiner.drop_system_columns(df)

    def execute_polars_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_key: str,
        right_key: str,
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Execute single-key join while preserving right join key as data column."""
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
        """Resolve qualified join key names for seed/enricher join."""
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
        """Resolve qualified join key names when left/right key names differ."""
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
        """Resolve all join keys for composite-key dependency join."""
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
        """Execute multi-key join preserving right-side key columns."""
        return self._join_executor.execute_composite_key_join(
            left_df,
            right_df,
            left_keys,
            right_keys,
            pipeline_name,
        )

    def get_polars_join_type(self) -> JoinHow:
        """Map MergeStrategy to Polars join type."""
        match self._config.strategy:
            case MergeStrategy.LEFT_OUTER:
                return "left"
            case MergeStrategy.INNER:
                return "inner"
            case MergeStrategy.UNION:
                return "full"
            case _:
                return "left"


class JoinPlannerService(JoinPlannerCompatibilityMixin):
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

    @staticmethod
    def _parse_pipeline_name(pipeline: str) -> tuple[str, str]:
        """Compatibility shim delegating to helper parser."""
        return parse_pipeline_name(pipeline)

    def __init__(
        self,
        merge_config: MergeConfig,
        logger: LoggerPort,
        deduplicator: EnricherDeduplicatorService,
        aggregator: EnricherAggregatorService,
        renamer: ColumnRenamerService,
        conflict_resolver: ConflictResolverService,
        field_alias_resolver: Callable[[str], dict[str, str] | None] | None = None,
        join_key_resolver: JoinKeyResolverProtocol | None = None,
        join_executor: JoinExecutorProtocol | None = None,
        dependency_joiner: DependencyJoinerProtocol | None = None,
    ) -> None:
        self._config = merge_config
        self._logger = logger
        self._deduplicator = deduplicator
        self._aggregator = aggregator
        self._renamer = renamer
        self._conflict_resolver = conflict_resolver
        self._field_alias_resolver = (
            field_alias_resolver or resolve_field_aliases_from_registry
        )
        self._join_key_resolver = join_key_resolver or JoinKeyResolverService(
            normalize_join_keys=self._NORMALIZE_JOIN_KEYS,
            parse_pipeline_name=self._parse_pipeline_name,
        )
        self._join_executor = join_executor or JoinExecutorService(
            logger=logger,
            join_type_resolver=self.get_polars_join_type,
        )
        self._dependency_joiner = dependency_joiner or DependencyJoinerService(
            logger=logger,
            deduplicator=deduplicator,
            renamer=renamer,
            conflict_resolver=conflict_resolver,
            field_alias_resolver=self._field_alias_resolver,
            join_key_resolver=self._join_key_resolver,
            join_executor=self._join_executor,
            system_columns_to_drop=self._SYSTEM_COLUMNS_TO_DROP,
        )

    async def apply_joins(
        self,
        seed_df: pl.DataFrame,
        enricher_dfs: dict[str, pl.DataFrame],
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Join successful enrichers to seed DataFrame."""
        merged = seed_df
        for enricher in enrichers:
            if enricher.pipeline not in enricher_dfs:
                continue

            merged = self._merge_single_enricher(
                merged_df=merged,
                enricher_df=enricher_dfs[enricher.pipeline],
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
        join_keys_list = list(enricher.join_keys)
        primary_key = join_keys_list[0]
        merged_df = self.normalize_join_key_columns(
            merged_df,
            join_keys_list,
            pipeline=seed_pipeline,
        )
        prepared_enricher_df = self._prepare_enricher_dataframe(
            enricher_df=enricher_df,
            enricher=enricher,
            join_keys_list=join_keys_list,
        )

        seed_join_key, enricher_join_key, join_key_set = (
            self._build_enricher_join_key_set(
                primary_key=primary_key,
                seed_pipeline=seed_pipeline,
                enricher_pipeline=enricher.pipeline,
                merged_columns=merged_df.columns,
            )
        )
        merged_df, prepared_enricher_df = (
            self._conflict_resolver.detect_and_resolve_conflicts(
                merged_df,
                prepared_enricher_df,
                join_key_set,
            )
        )
        return self.execute_polars_join(
            merged_df,
            prepared_enricher_df,
            seed_join_key,
            enricher_join_key,
            enricher.pipeline,
        )

    def _prepare_enricher_dataframe(
        self,
        *,
        enricher_df: pl.DataFrame,
        enricher: EnricherConfig,
        join_keys_list: list[str],
    ) -> pl.DataFrame:
        prepared_df = enricher_df
        if enricher.is_many_to_one and enricher.aggregation is not None:
            prepared_df = self._aggregator.aggregate(
                prepared_df,
                enricher.aggregation,
                enricher.pipeline,
            )
        prepared_df = self._deduplicator.deduplicate(
            enricher_df=prepared_df,
            join_keys=join_keys_list,
            enricher_name=enricher.pipeline,
        )
        prepared_df = self.normalize_join_key_columns(
            prepared_df,
            join_keys_list,
            pipeline=None,
        )
        prepared_df = self._renamer.rename_dataframe(
            prepared_df,
            enricher.pipeline,
            exclude_join_keys=False,
            field_aliases=self._field_alias_resolver(enricher.pipeline),
        )
        self._logger.debug(
            "Renamed enricher columns to qualified format",
            enricher=enricher.pipeline,
            qualified_count=self._count_qualified_columns(prepared_df.columns),
        )
        return self.drop_system_columns(prepared_df)

    def _build_enricher_join_key_set(
        self,
        *,
        primary_key: str,
        seed_pipeline: str | None,
        enricher_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, set[str]]:
        seed_join_key, enricher_join_key, seed_join_key_qualified = (
            self.resolve_join_key_names(
                primary_key,
                seed_pipeline,
                enricher_pipeline,
                merged_columns,
            )
        )
        join_key_set = {seed_join_key, enricher_join_key}
        if seed_join_key_qualified and seed_join_key_qualified != seed_join_key:
            join_key_set.add(seed_join_key_qualified)
        return seed_join_key, enricher_join_key, join_key_set

    @staticmethod
    def _count_qualified_columns(columns: list[str]) -> int:
        return len([col for col in columns if "." in col and not col.startswith("_")])

    async def apply_dependency_joins(
        self,
        merged_df: pl.DataFrame,
        dependency_dfs: dict[str, pl.DataFrame],
        dependencies: Sequence[DependencyConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply configured dependency joins to merged DataFrame."""
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
        """Join dependency using all configured composite join keys."""
        return self._dependency_joiner.apply_composite_key_dependency_join(
            merged_df=merged_df,
            dep_df=dep_df,
            dep=dep,
            seed_pipeline=seed_pipeline,
        )


