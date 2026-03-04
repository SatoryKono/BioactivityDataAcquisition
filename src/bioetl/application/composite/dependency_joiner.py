"""Dependency join orchestration for composite merge pipelines."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from bioetl.application.composite.protocols import (
    JoinExecutorProtocol,
    JoinKeyResolverProtocol,
)

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.column_renamer import ColumnRenamerService
    from bioetl.application.composite.conflict_resolver import ConflictResolverService
    from bioetl.application.composite.deduplication import EnricherDeduplicatorService
    from bioetl.domain.composite.config import DependencyConfig
    from bioetl.domain.ports import LoggerPort


__all__ = ["DependencyJoinerService"]


def _log_missing_composite_key_columns(
    *,
    logger: LoggerPort,
    dependency: str,
    missing_left: list[str],
    missing_right: list[str],
) -> None:
    logger.warning(
        "Composite key join skipped: missing columns",
        dependency=dependency,
        missing_left=missing_left,
        missing_right=missing_right,
    )


class DependencyJoinerService:
    """Encapsulates dependency join preparation and execution logic."""

    def __init__(
        self,
        *,
        logger: LoggerPort,
        deduplicator: EnricherDeduplicatorService,
        renamer: ColumnRenamerService,
        conflict_resolver: ConflictResolverService,
        field_alias_resolver: Callable[[str], dict[str, str] | None],
        join_key_resolver: JoinKeyResolverProtocol,
        join_executor: JoinExecutorProtocol,
        system_columns_to_drop: frozenset[str],
    ) -> None:
        self._logger = logger
        self._deduplicator = deduplicator
        self._renamer = renamer
        self._conflict_resolver = conflict_resolver
        self._field_alias_resolver = field_alias_resolver
        self._join_key_resolver = join_key_resolver
        self._join_executor = join_executor
        self._system_columns_to_drop = system_columns_to_drop

    def apply_dependency_joins(
        self,
        *,
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
                    merged_df=result,
                    dep_df=dep_df,
                    dep=dep,
                    seed_pipeline=seed_pipeline,
                )
                continue

            result = self._apply_single_key_dependency_join(
                result=result,
                dep_df=dep_df,
                dep=dep,
                seed_pipeline=seed_pipeline,
            )

        return result

    def apply_composite_key_dependency_join(
        self,
        *,
        merged_df: pl.DataFrame,
        dep_df: pl.DataFrame,
        dep: DependencyConfig,
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Join dependency using all configured composite join keys."""
        join_keys_list = list(dep.join_keys)
        left_pipeline = self._resolve_left_pipeline(dep, seed_pipeline)

        dep_df = self._prepare_dependency_dataframe(
            dep_df=dep_df,
            dep=dep,
            deduplicate_keys=join_keys_list,
        )
        merged_df, dep_df = self._normalize_dependency_join_inputs(
            merged_df=merged_df,
            dep_df=dep_df,
            left_join_keys=join_keys_list,
            right_join_keys=join_keys_list,
            seed_pipeline=seed_pipeline,
        )
        dep_df = self._rename_dependency_dataframe(
            dep_df=dep_df,
            dependency=dep.pipeline,
        )
        left_keys, right_keys, all_join_key_set = (
            self._join_key_resolver.resolve_composite_join_keys(
                join_keys_list,
                left_pipeline,
                dep.pipeline,
                merged_df.columns,
            )
        )
        merged_df, dep_df = self._conflict_resolver.detect_and_resolve_conflicts(
            merged_df,
            dep_df,
            all_join_key_set,
        )
        missing_left = [key for key in left_keys if key not in merged_df.columns]
        missing_right = [key for key in right_keys if key not in dep_df.columns]
        if missing_left or missing_right:
            _log_missing_composite_key_columns(
                logger=self._logger,
                dependency=dep.pipeline,
                missing_left=missing_left,
                missing_right=missing_right,
            )
            return merged_df

        result = self._join_executor.execute_composite_key_join(
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

    def drop_system_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Drop system columns that must come only from seed."""
        columns_to_drop = [
            column for column in df.columns if column in self._system_columns_to_drop
        ]
        if not columns_to_drop:
            return df

        self._logger.debug(
            "Dropping system columns from enricher",
            columns=columns_to_drop,
        )
        return df.drop(columns_to_drop)

    def _apply_single_key_dependency_join(
        self,
        *,
        result: pl.DataFrame,
        dep_df: pl.DataFrame,
        dep: DependencyConfig,
        seed_pipeline: str | None,
    ) -> pl.DataFrame:
        join_keys_list = list(dep.join_keys)
        primary_key = join_keys_list[0]
        right_key = dep.filter_field if dep.filter_field else primary_key
        right_keys_list = [right_key] if dep.filter_field else join_keys_list
        left_pipeline = self._resolve_left_pipeline(dep, seed_pipeline)

        dep_df = self._prepare_dependency_dataframe(
            dep_df=dep_df,
            dep=dep,
            deduplicate_keys=right_keys_list,
        )
        result, dep_df = self._normalize_dependency_join_inputs(
            merged_df=result,
            dep_df=dep_df,
            left_join_keys=join_keys_list,
            right_join_keys=right_keys_list,
            seed_pipeline=seed_pipeline,
        )
        dep_df = self._rename_dependency_dataframe(
            dep_df=dep_df,
            dependency=dep.pipeline,
        )
        seed_join_key, dep_join_key, seed_join_key_qualified = (
            self._join_key_resolver.resolve_join_key_names_asymmetric(
                left_key=primary_key,
                right_key=right_key,
                left_pipeline=left_pipeline,
                right_pipeline=dep.pipeline,
                merged_columns=result.columns,
            )
        )

        join_key_set = self._build_asymmetric_join_key_set(
            left_join_key=seed_join_key,
            right_join_key=dep_join_key,
            left_join_key_qualified=seed_join_key_qualified,
        )

        result, dep_df = self._conflict_resolver.detect_and_resolve_conflicts(
            result,
            dep_df,
            join_key_set,
        )
        result = self._join_executor.execute_polars_join(
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

    @staticmethod
    def _resolve_left_pipeline(
        dep: DependencyConfig,
        seed_pipeline: str | None,
    ) -> str | None:
        if dep.key_source and dep.key_source != "seed":
            return dep.key_source
        return seed_pipeline

    def _prepare_dependency_dataframe(
        self,
        *,
        dep_df: pl.DataFrame,
        dep: DependencyConfig,
        deduplicate_keys: list[str],
    ) -> pl.DataFrame:
        return self._deduplicator.deduplicate(
            enricher_df=dep_df,
            join_keys=deduplicate_keys,
            enricher_name=dep.pipeline,
        )

    def _normalize_dependency_join_inputs(
        self,
        *,
        merged_df: pl.DataFrame,
        dep_df: pl.DataFrame,
        left_join_keys: list[str],
        right_join_keys: list[str],
        seed_pipeline: str | None,
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        normalized_merged = self._join_key_resolver.normalize_join_key_columns(
            merged_df,
            left_join_keys,
            pipeline=seed_pipeline,
        )
        normalized_dep = self._join_key_resolver.normalize_join_key_columns(
            dep_df,
            right_join_keys,
            pipeline=None,
        )
        return normalized_merged, normalized_dep

    def _rename_dependency_dataframe(
        self,
        *,
        dep_df: pl.DataFrame,
        dependency: str,
    ) -> pl.DataFrame:
        renamed = self._renamer.rename_dataframe(
            dep_df,
            dependency,
            exclude_join_keys=False,
            field_aliases=self._field_alias_resolver(dependency),
        )
        self._logger.debug(
            "Renamed dependency columns to qualified format",
            dependency=dependency,
            qualified_count=len(
                [
                    col
                    for col in renamed.columns
                    if "." in col and not col.startswith("_")
                ]
            ),
        )
        return self.drop_system_columns(renamed)

    @staticmethod
    def _build_asymmetric_join_key_set(
        *,
        left_join_key: str,
        right_join_key: str,
        left_join_key_qualified: str | None,
    ) -> set[str]:
        join_key_set = {left_join_key, right_join_key}
        if left_join_key_qualified and left_join_key_qualified != left_join_key:
            join_key_set.add(left_join_key_qualified)
        return join_key_set
