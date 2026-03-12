"""Dependency join orchestration for composite merge pipelines."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from bioetl.application.composite.dependency_join_support import (
    PreparedDependencyJoinContext,
    build_asymmetric_join_key_set,
    build_composite_join_metadata,
    build_single_key_join_metadata,
    execute_dependency_join,
    find_missing_keys,
    log_missing_composite_key_columns,
    prepare_dependency_join_frames,
)
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
        """Initialise the dependency joiner with all required collaborator services."""
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
                merged_df=result,
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
        metadata = build_composite_join_metadata(
            dep=dep,
            seed_pipeline=seed_pipeline,
        )
        prepared_context = self._prepare_dependency_join_context(
            merged_df=merged_df,
            dep_df=dep_df,
            dep=dep,
            left_join_keys=metadata.join_keys_list,
            right_join_keys=metadata.join_keys_list,
            seed_pipeline=seed_pipeline,
        )
        left_keys, right_keys, all_join_key_set = (
            self._join_key_resolver.resolve_composite_join_keys(
                metadata.join_keys_list,
                metadata.left_pipeline,
                dep.pipeline,
                prepared_context.merged_df.columns,
            )
        )
        merged_df, dep_df = self._conflict_resolver.detect_and_resolve_conflicts(
            prepared_context.merged_df,
            prepared_context.dep_df,
            all_join_key_set,
        )
        missing_left = find_missing_keys(merged_df.columns, left_keys)
        missing_right = find_missing_keys(dep_df.columns, right_keys)
        if missing_left or missing_right:
            log_missing_composite_key_columns(
                logger=self._logger,
                dependency=dep.pipeline,
                missing_left=missing_left,
                missing_right=missing_right,
            )
            return merged_df

        return execute_dependency_join(
            conflict_resolver=self._conflict_resolver,
            logger=self._logger,
            merged_df=merged_df,
            dep_df=dep_df,
            join_key_set=all_join_key_set,
            execute_join=lambda resolved_merged, resolved_dep: (
                self._join_executor.execute_composite_key_join(
                    resolved_merged,
                    resolved_dep,
                    left_keys,
                    right_keys,
                    dep.pipeline,
                )
            ),
            log_message="Joined dependency with composite key",
            dependency=dep.pipeline,
            log_fields={"left_keys": left_keys, "right_keys": right_keys},
        )

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
        merged_df: pl.DataFrame,
        dep_df: pl.DataFrame,
        dep: DependencyConfig,
        seed_pipeline: str | None,
    ) -> pl.DataFrame:
        metadata = build_single_key_join_metadata(
            dep=dep,
            seed_pipeline=seed_pipeline,
        )
        prepared_context = self._prepare_dependency_join_context(
            merged_df=merged_df,
            dep_df=dep_df,
            dep=dep,
            left_join_keys=metadata.join_keys_list,
            right_join_keys=metadata.right_keys_list,
            seed_pipeline=seed_pipeline,
        )
        seed_join_key, dep_join_key, seed_join_key_qualified = (
            self._join_key_resolver.resolve_join_key_names_asymmetric(
                left_key=metadata.primary_key,
                right_key=metadata.right_key,
                left_pipeline=metadata.left_pipeline,
                right_pipeline=dep.pipeline,
                merged_columns=prepared_context.merged_df.columns,
            )
        )

        join_key_set = build_asymmetric_join_key_set(
            left_join_key=seed_join_key,
            right_join_key=dep_join_key,
            left_join_key_qualified=seed_join_key_qualified,
        )

        return execute_dependency_join(
            conflict_resolver=self._conflict_resolver,
            logger=self._logger,
            merged_df=prepared_context.merged_df,
            dep_df=prepared_context.dep_df,
            join_key_set=join_key_set,
            execute_join=lambda resolved_merged, resolved_dep: (
                self._join_executor.execute_polars_join(
                    resolved_merged,
                    resolved_dep,
                    seed_join_key,
                    dep_join_key,
                    dep.pipeline,
                )
            ),
            log_message="Joined dependency",
            dependency=dep.pipeline,
            log_fields={
                "seed_join_key": seed_join_key,
                "dep_join_key": dep_join_key,
            },
        )

    def _prepare_dependency_join_context(
        self,
        *,
        merged_df: pl.DataFrame,
        dep_df: pl.DataFrame,
        dep: DependencyConfig,
        left_join_keys: list[str],
        right_join_keys: list[str],
        seed_pipeline: str | None,
    ) -> PreparedDependencyJoinContext:
        prepared_merged_df, prepared_dep_df = prepare_dependency_join_frames(
            deduplicator=self._deduplicator,
            join_key_resolver=self._join_key_resolver,
            renamer=self._renamer,
            logger=self._logger,
            field_alias_resolver=self._field_alias_resolver,
            drop_system_columns=self.drop_system_columns,
            merged_df=merged_df,
            dep_df=dep_df,
            dep=dep,
            left_join_keys=left_join_keys,
            right_join_keys=right_join_keys,
            seed_pipeline=seed_pipeline,
        )
        return PreparedDependencyJoinContext(
            merged_df=prepared_merged_df,
            dep_df=prepared_dep_df,
        )
