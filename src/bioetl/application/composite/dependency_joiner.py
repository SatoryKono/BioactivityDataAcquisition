"""Dependency join orchestration for composite merge pipelines."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from bioetl.application.composite.dependency_join_apply_ops import (
    apply_composite_key_dependency_join as _apply_composite_key_dependency_join_op,
)
from bioetl.application.composite.dependency_join_apply_ops import (
    apply_single_key_dependency_join as _apply_single_key_dependency_join_op,
)
from bioetl.application.composite.target_protein_classification_summary import (
    TARGET_PROTEIN_CLASSIFICATION_PIPELINE,
    summarize_target_protein_classification_dependency,
)

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.column_renamer import ColumnRenamer
    from bioetl.application.composite.conflict_resolver import ConflictResolverService
    from bioetl.application.composite.deduplication import EnricherDeduplicatorService
    from bioetl.application.composite.protocols import (
        JoinExecutorProtocol,
        JoinKeyResolverProtocol,
    )
    from bioetl.domain.composite import DependencyConfig
    from bioetl.domain.ports import LoggerPort

__all__ = ["DependencyJoinerService"]


class DependencyJoinerService:
    """Encapsulates dependency join preparation and execution logic."""

    def __init__(
        self,
        *,
        logger: LoggerPort,
        deduplicator: EnricherDeduplicatorService,
        renamer: ColumnRenamer,
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
            result = self._apply_loaded_dependency_join(
                merged_df=result,
                dependency_dfs=dependency_dfs,
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
        return _apply_composite_key_dependency_join_op(
            deduplicator=self._deduplicator,
            join_key_resolver=self._join_key_resolver,
            renamer=self._renamer,
            logger=self._logger,
            field_alias_resolver=self._field_alias_resolver,
            drop_system_columns=self.drop_system_columns,
            conflict_resolver=self._conflict_resolver,
            join_executor=self._join_executor,
            merged_df=merged_df,
            dep_df=dep_df,
            dep=dep,
            seed_pipeline=seed_pipeline,
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
        return _apply_single_key_dependency_join_op(
            deduplicator=self._deduplicator,
            join_key_resolver=self._join_key_resolver,
            renamer=self._renamer,
            logger=self._logger,
            field_alias_resolver=self._field_alias_resolver,
            drop_system_columns=self.drop_system_columns,
            conflict_resolver=self._conflict_resolver,
            join_executor=self._join_executor,
            merged_df=merged_df,
            dep_df=dep_df,
            dep=dep,
            seed_pipeline=seed_pipeline,
        )

    def _apply_loaded_dependency_join(
        self,
        *,
        merged_df: pl.DataFrame,
        dependency_dfs: dict[str, pl.DataFrame],
        dep: DependencyConfig,
        seed_pipeline: str | None,
    ) -> pl.DataFrame:
        """Skip unloaded dependencies and route loaded ones to the right join flow."""
        dep_df = dependency_dfs.get(dep.pipeline)
        if dep_df is None:
            return merged_df
        if dep.pipeline == TARGET_PROTEIN_CLASSIFICATION_PIPELINE:
            dep_df = summarize_target_protein_classification_dependency(dep_df)

        return self._apply_resolved_dependency_join(
            merged_df=merged_df,
            dep_df=dep_df,
            dep=dep,
            seed_pipeline=seed_pipeline,
        )

    def _apply_resolved_dependency_join(
        self,
        *,
        merged_df: pl.DataFrame,
        dep_df: pl.DataFrame,
        dep: DependencyConfig,
        seed_pipeline: str | None,
    ) -> pl.DataFrame:
        """Route a loaded dependency to its composite-key or single-key execution path."""
        if dep.is_multi_field_filter:
            return self.apply_composite_key_dependency_join(
                merged_df=merged_df,
                dep_df=dep_df,
                dep=dep,
                seed_pipeline=seed_pipeline,
            )

        return self._apply_single_key_dependency_join(
            merged_df=merged_df,
            dep_df=dep_df,
            dep=dep,
            seed_pipeline=seed_pipeline,
        )
