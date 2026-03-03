"""Join planning and execution for composite merge pipeline."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Literal

from bioetl.domain.composite.strategy import MergeStrategy

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.aggregator import EnricherAggregator
    from bioetl.application.composite.column_renamer import ColumnRenamer
    from bioetl.application.composite.conflict_resolver import ConflictResolver
    from bioetl.application.composite.deduplication import EnricherDeduplicator
    from bioetl.domain.composite.config import (
        DependencyConfig,
        EnricherConfig,
        MergeConfig,
    )
    from bioetl.domain.ports import LoggerPort


JoinHow = Literal["inner", "left", "right", "full", "semi", "anti", "cross", "outer"]


class JoinPlanner:
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

    def __init__(
        self,
        merge_config: MergeConfig,
        logger: LoggerPort,
        deduplicator: EnricherDeduplicator,
        aggregator: EnricherAggregator,
        renamer: ColumnRenamer,
        conflict_resolver: ConflictResolver,
        field_alias_resolver: Callable[[str], dict[str, str] | None],
    ) -> None:
        self._config = merge_config
        self._logger = logger
        self._deduplicator = deduplicator
        self._aggregator = aggregator
        self._renamer = renamer
        self._conflict_resolver = conflict_resolver
        self._field_alias_resolver = field_alias_resolver

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

            enricher_df = enricher_dfs[enricher.pipeline]
            join_keys_list = list(enricher.join_keys)
            primary_key = join_keys_list[0]

            if enricher.is_many_to_one and enricher.aggregation is not None:
                enricher_df = self._aggregator.aggregate(
                    enricher_df,
                    enricher.aggregation,
                    enricher.pipeline,
                )

            enricher_df = self._deduplicator.deduplicate(
                enricher_df=enricher_df,
                join_keys=join_keys_list,
                enricher_name=enricher.pipeline,
            )

            merged = self.normalize_join_key_columns(
                merged,
                join_keys_list,
                pipeline=seed_pipeline,
            )
            enricher_df = self.normalize_join_key_columns(
                enricher_df,
                join_keys_list,
                pipeline=None,
            )

            enricher_df = self._renamer.rename_dataframe(
                enricher_df,
                enricher.pipeline,
                exclude_join_keys=False,
                field_aliases=self._field_alias_resolver(enricher.pipeline),
            )

            self._logger.debug(
                "Renamed enricher columns to qualified format",
                enricher=enricher.pipeline,
                qualified_count=len(
                    [
                        col
                        for col in enricher_df.columns
                        if "." in col and not col.startswith("_")
                    ]
                ),
            )

            enricher_df = self.drop_system_columns(enricher_df)
            seed_join_key, enricher_join_key, seed_join_key_qualified = (
                self.resolve_join_key_names(
                    primary_key,
                    seed_pipeline,
                    enricher.pipeline,
                    merged.columns,
                )
            )

            join_key_set = {seed_join_key, enricher_join_key}
            if seed_join_key_qualified and seed_join_key_qualified != seed_join_key:
                join_key_set.add(seed_join_key_qualified)

            merged, enricher_df = self._conflict_resolver.detect_and_resolve_conflicts(
                merged,
                enricher_df,
                join_key_set,
            )

            merged = self.execute_polars_join(
                merged,
                enricher_df,
                seed_join_key,
                enricher_join_key,
                enricher.pipeline,
            )

        return merged

    async def apply_dependency_joins(
        self,
        merged_df: pl.DataFrame,
        dependency_dfs: dict[str, pl.DataFrame],
        dependencies: Sequence[DependencyConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply configured dependency joins to merged DataFrame."""
        result = merged_df

        for dep in dependencies:
            if dep.pipeline not in dependency_dfs:
                continue

            dep_df = dependency_dfs[dep.pipeline]

            if dep.is_multi_field_filter:
                result = self.apply_composite_key_dependency_join(
                    result,
                    dep_df,
                    dep,
                    seed_pipeline,
                )
                continue

            join_keys_list = list(dep.join_keys)
            primary_key = join_keys_list[0]
            right_key = dep.filter_field if dep.filter_field else primary_key
            right_keys_list = [right_key] if dep.filter_field else join_keys_list

            dep_df = self._deduplicator.deduplicate(
                enricher_df=dep_df,
                join_keys=right_keys_list,
                enricher_name=dep.pipeline,
            )

            result = self.normalize_join_key_columns(
                result,
                join_keys_list,
                pipeline=seed_pipeline,
            )
            dep_df = self.normalize_join_key_columns(
                dep_df,
                right_keys_list,
                pipeline=None,
            )

            dep_df = self._renamer.rename_dataframe(
                dep_df,
                dep.pipeline,
                exclude_join_keys=False,
                field_aliases=self._field_alias_resolver(dep.pipeline),
            )

            self._logger.debug(
                "Renamed dependency columns to qualified format",
                dependency=dep.pipeline,
                qualified_count=len(
                    [col for col in dep_df.columns if "." in col and not col.startswith("_")]
                ),
            )

            dep_df = self.drop_system_columns(dep_df)

            left_pipeline = (
                dep.key_source
                if dep.key_source and dep.key_source != "seed"
                else seed_pipeline
            )

            seed_join_key, dep_join_key, seed_join_key_qualified = (
                self.resolve_join_key_names_asymmetric(
                    left_key=primary_key,
                    right_key=right_key,
                    left_pipeline=left_pipeline,
                    right_pipeline=dep.pipeline,
                    merged_columns=result.columns,
                )
            )

            join_key_set = {seed_join_key, dep_join_key}
            if seed_join_key_qualified and seed_join_key_qualified != seed_join_key:
                join_key_set.add(seed_join_key_qualified)

            result, dep_df = self._conflict_resolver.detect_and_resolve_conflicts(
                result,
                dep_df,
                join_key_set,
            )

            result = self.execute_polars_join(
                result,
                dep_df,
                seed_join_key,
                dep_join_key,
                dep.pipeline,
            )

            self._logger.debug(
                "Joined dependency",
                dependency=dep.pipeline,
                seed_join_key=seed_join_key,
                dep_join_key=dep_join_key,
                result_rows=len(result),
            )

        return result

    def apply_composite_key_dependency_join(
        self,
        merged_df: pl.DataFrame,
        dep_df: pl.DataFrame,
        dep: DependencyConfig,
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Join dependency using all configured composite join keys."""
        join_keys_list = list(dep.join_keys)

        dep_df = self._deduplicator.deduplicate(
            enricher_df=dep_df,
            join_keys=join_keys_list,
            enricher_name=dep.pipeline,
        )

        merged_df = self.normalize_join_key_columns(
            merged_df,
            join_keys_list,
            pipeline=seed_pipeline,
        )
        dep_df = self.normalize_join_key_columns(dep_df, join_keys_list, pipeline=None)

        dep_df = self._renamer.rename_dataframe(
            dep_df,
            dep.pipeline,
            exclude_join_keys=False,
            field_aliases=self._field_alias_resolver(dep.pipeline),
        )
        dep_df = self.drop_system_columns(dep_df)

        left_pipeline = (
            dep.key_source
            if dep.key_source and dep.key_source != "seed"
            else seed_pipeline
        )
        left_keys, right_keys, all_join_key_set = self.resolve_composite_join_keys(
            join_keys_list,
            left_pipeline,
            dep.pipeline,
            merged_df.columns,
        )

        merged_df, dep_df = self._conflict_resolver.detect_and_resolve_conflicts(
            merged_df,
            dep_df,
            all_join_key_set,
        )

        missing_left = [key for key in left_keys if key not in merged_df.columns]
        missing_right = [key for key in right_keys if key not in dep_df.columns]
        if missing_left or missing_right:
            self._logger.warning(
                "Composite key join skipped: missing columns",
                dependency=dep.pipeline,
                missing_left=missing_left,
                missing_right=missing_right,
            )
            return merged_df

        result = self.execute_composite_key_join(
            merged_df,
            dep_df,
            left_keys,
            right_keys,
            dep.pipeline,
        )

        self._logger.debug(
            "Joined dependency with composite key",
            dependency=dep.pipeline,
            left_keys=left_keys,
            right_keys=right_keys,
            result_rows=len(result),
        )

        return result

    def find_join_key_column(
        self,
        key: str,
        columns: list[str],
        pipeline: str | None = None,
    ) -> str | None:
        """Find key column name (qualified preferred, fallback unqualified)."""
        if pipeline:
            try:
                provider, entity = self._parse_pipeline_name(pipeline)
                qualified = f"{provider}.{entity}.{key}"
                if qualified in columns:
                    return qualified
            except ValueError:
                pass

        if key in columns:
            return key

        return next((col for col in columns if col.endswith(f".{key}")), None)

    def normalize_join_key_columns(
        self,
        df: pl.DataFrame,
        join_keys: list[str],
        pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Normalize selected identifier join key columns to lowercase."""
        import polars as pl

        columns = df.columns
        normalize = [
            column
            for key in join_keys
            if key in self._NORMALIZE_JOIN_KEYS
            if (column := self.find_join_key_column(key, columns, pipeline))
        ]

        if not normalize:
            return df

        return df.with_columns(
            [pl.col(column).str.to_lowercase().alias(column) for column in normalize]
        )

    def drop_system_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Drop system columns that must come only from seed."""
        columns_to_drop = [
            column for column in df.columns if column in self._SYSTEM_COLUMNS_TO_DROP
        ]
        if not columns_to_drop:
            return df

        self._logger.debug(
            "Dropping system columns from enricher",
            columns=columns_to_drop,
        )
        return df.drop(columns_to_drop)

    def execute_polars_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_key: str,
        right_key: str,
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Execute single-key join while preserving right join key as data column."""
        import polars as pl

        how = self.get_polars_join_type()

        if left_key not in left_df.columns or right_key not in right_df.columns:
            self._logger.warning(
                "Join skipped: key not found in columns",
                pipeline=pipeline_name,
                left_key=left_key,
                right_key=right_key,
                left_columns=left_df.columns if left_key not in left_df.columns else None,
                right_columns=right_df.columns if right_key not in right_df.columns else None,
            )
            return left_df

        if left_df[left_key].dtype != right_df[right_key].dtype:
            self._logger.debug(
                "Coercing join keys to String due to type mismatch",
                pipeline=pipeline_name,
                left_key=left_key,
                left_type=str(left_df[left_key].dtype),
                right_key=right_key,
                right_type=str(right_df[right_key].dtype),
            )
            left_df = left_df.with_columns(
                pl.col(left_key).cast(pl.String).str.replace(r"\\.0$", "", literal=False)
            )
            right_df = right_df.with_columns(
                pl.col(right_key)
                .cast(pl.String)
                .str.replace(r"\\.0$", "", literal=False)
            )

        if left_key != right_key:
            temp_join_col = f"__temp_join_{pipeline_name}"
            right_df = right_df.with_columns(pl.col(right_key).alias(temp_join_col))
            return left_df.join(
                right_df,
                left_on=left_key,
                right_on=temp_join_col,
                how=how,
                suffix=f"_{pipeline_name}",
            )

        return left_df.join(
            right_df,
            left_on=left_key,
            right_on=right_key,
            how=how,
            suffix=f"_{pipeline_name}",
        )

    def resolve_join_key_names(
        self,
        primary_key: str,
        seed_pipeline: str | None,
        enricher_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, str | None]:
        """Resolve qualified join key names for seed/enricher join."""
        seed_join_key_qualified: str | None = None
        seed_join_key = primary_key

        if seed_pipeline is not None:
            try:
                seed_provider, seed_entity = self._parse_pipeline_name(seed_pipeline)
                seed_join_key_qualified = f"{seed_provider}.{seed_entity}.{primary_key}"
                if seed_join_key_qualified in merged_columns:
                    seed_join_key = seed_join_key_qualified
            except ValueError:
                pass

        try:
            enricher_provider, enricher_entity = self._parse_pipeline_name(
                enricher_pipeline
            )
            enricher_join_key = f"{enricher_provider}.{enricher_entity}.{primary_key}"
        except ValueError:
            enricher_join_key = primary_key

        return seed_join_key, enricher_join_key, seed_join_key_qualified

    def resolve_join_key_names_asymmetric(
        self,
        left_key: str,
        right_key: str,
        left_pipeline: str | None,
        right_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, str | None]:
        """Resolve qualified join key names when left/right key names differ."""
        left_join_key_qualified: str | None = None
        left_join_key = left_key

        if left_pipeline is not None:
            try:
                left_provider, left_entity = self._parse_pipeline_name(left_pipeline)
                left_join_key_qualified = f"{left_provider}.{left_entity}.{left_key}"
                if left_join_key_qualified in merged_columns:
                    left_join_key = left_join_key_qualified
            except ValueError:
                pass

        try:
            right_provider, right_entity = self._parse_pipeline_name(right_pipeline)
            right_join_key = f"{right_provider}.{right_entity}.{right_key}"
        except ValueError:
            right_join_key = right_key

        return left_join_key, right_join_key, left_join_key_qualified

    def resolve_composite_join_keys(
        self,
        join_keys_list: list[str],
        left_pipeline: str | None,
        right_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[list[str], list[str], set[str]]:
        """Resolve all join keys for composite-key dependency join."""
        left_keys: list[str] = []
        right_keys: list[str] = []
        all_join_key_set: set[str] = set()

        for key in join_keys_list:
            left_key, right_key, left_key_qualified = (
                self.resolve_join_key_names_asymmetric(
                    left_key=key,
                    right_key=key,
                    left_pipeline=left_pipeline,
                    right_pipeline=right_pipeline,
                    merged_columns=merged_columns,
                )
            )
            left_keys.append(left_key)
            right_keys.append(right_key)
            all_join_key_set.add(left_key)
            all_join_key_set.add(right_key)
            if left_key_qualified and left_key_qualified != left_key:
                all_join_key_set.add(left_key_qualified)

        return left_keys, right_keys, all_join_key_set

    def execute_composite_key_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_keys: list[str],
        right_keys: list[str],
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Execute multi-key join preserving right-side key columns."""
        import polars as pl

        how = self.get_polars_join_type()
        if left_keys == right_keys:
            return left_df.join(
                right_df,
                on=left_keys,
                how=how,
                suffix=f"_{pipeline_name}",
            )

        temp_cols: list[str] = []
        for left_key, right_key in zip(left_keys, right_keys, strict=True):
            if left_key != right_key:
                temp_col = f"__temp_join_{pipeline_name}_{right_key}"
                right_df = right_df.with_columns(pl.col(right_key).alias(temp_col))
                temp_cols.append(temp_col)
            else:
                temp_cols.append(right_key)

        return left_df.join(
            right_df,
            left_on=left_keys,
            right_on=temp_cols,
            how=how,
            suffix=f"_{pipeline_name}",
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

    @staticmethod
    def _parse_pipeline_name(pipeline: str) -> tuple[str, str]:
        """Parse provider_entity pipeline name into tuple."""
        if "_" not in pipeline:
            raise ValueError(
                f"Pipeline name '{pipeline}' must be in format 'provider_entity'"
            )
        provider, entity = pipeline.split("_", 1)
        return provider, entity
