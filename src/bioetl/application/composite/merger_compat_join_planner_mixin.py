"""Join planner compatibility mixin for MergeService facade."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.join_planner import JoinHow, JoinPlannerService

if TYPE_CHECKING:
    from collections.abc import Sequence

    import polars as pl

    from bioetl.domain.composite.config import DependencyConfig, EnricherConfig


class _MergeCompatibilityJoinPlannerMixin:
    """Join-planner delegation wrappers preserved for compatibility."""

    _join_planner: JoinPlannerService
    _conflict_resolver: ConflictResolverService

    def _find_join_key_column(
        self,
        key: str,
        columns: list[str],
        pipeline: str | None = None,
    ) -> str | None:
        """Compatibility wrapper for join-key column lookup."""
        return self._join_planner.find_join_key_column(key, columns, pipeline)

    def _normalize_join_key_columns(
        self,
        df: pl.DataFrame,
        join_keys: list[str],
        pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for join-key normalization."""
        return self._join_planner.normalize_join_key_columns(df, join_keys, pipeline)

    def _find_next_suffix(self, base_col: str, existing_cols: set[str]) -> str:
        """Compatibility wrapper for suffix allocation."""
        return self._conflict_resolver.find_next_suffix(base_col, existing_cols)

    def _detect_and_resolve_conflicts(
        self,
        seed_df: pl.DataFrame,
        enricher_df: pl.DataFrame,
        join_keys: set[str],
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Compatibility wrapper for conflict detection and renaming."""
        return self._conflict_resolver.detect_and_resolve_conflicts(
            seed_df,
            enricher_df,
            join_keys,
        )

    async def _apply_joins(
        self,
        seed_df: pl.DataFrame,
        enricher_dfs: dict[str, pl.DataFrame],
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for enricher joins."""
        return await self._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs=enricher_dfs,
            enrichers=enrichers,
            seed_pipeline=seed_pipeline,
        )

    def _execute_polars_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_key: str,
        right_key: str,
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Compatibility wrapper for single-key Polars join."""
        return self._join_planner.execute_polars_join(
            left_df,
            right_df,
            left_key,
            right_key,
            pipeline_name,
        )

    async def _apply_dependency_joins(
        self,
        merged_df: pl.DataFrame,
        dependency_dfs: dict[str, pl.DataFrame],
        dependencies: Sequence[DependencyConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for dependency joins."""
        return await self._join_planner.apply_dependency_joins(
            merged_df=merged_df,
            dependency_dfs=dependency_dfs,
            dependencies=dependencies,
            seed_pipeline=seed_pipeline,
        )

    def _resolve_composite_join_keys(
        self,
        join_keys_list: list[str],
        left_pipeline: str | None,
        right_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[list[str], list[str], set[str]]:
        """Compatibility wrapper for composite join-key resolution."""
        return self._join_planner.resolve_composite_join_keys(
            join_keys_list,
            left_pipeline,
            right_pipeline,
            merged_columns,
        )

    def _execute_composite_key_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_keys: list[str],
        right_keys: list[str],
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Compatibility wrapper for composite-key join."""
        return self._join_planner.execute_composite_key_join(
            left_df,
            right_df,
            left_keys,
            right_keys,
            pipeline_name,
        )

    def _apply_composite_key_dependency_join(
        self,
        merged_df: pl.DataFrame,
        dep_df: pl.DataFrame,
        dep: DependencyConfig,
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for composite-key dependency joins."""
        return self._join_planner.apply_composite_key_dependency_join(
            merged_df,
            dep_df,
            dep,
            seed_pipeline,
        )

    def _get_polars_join_type(self) -> JoinHow:
        """Compatibility wrapper for join strategy mapping."""
        return self._join_planner.get_polars_join_type()

    def _drop_system_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Compatibility wrapper for system-column cleanup."""
        return self._join_planner.drop_system_columns(df)

    def _resolve_join_key_names(
        self,
        primary_key: str,
        seed_pipeline: str | None,
        enricher_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, str | None]:
        """Compatibility wrapper for symmetric join-key resolution."""
        return self._join_planner.resolve_join_key_names(
            primary_key,
            seed_pipeline,
            enricher_pipeline,
            merged_columns,
        )

    def _resolve_join_key_names_asymmetric(
        self,
        left_key: str,
        right_key: str,
        left_pipeline: str | None,
        right_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, str | None]:
        """Compatibility wrapper for asymmetric join-key resolution."""
        return self._join_planner.resolve_join_key_names_asymmetric(
            left_key,
            right_key,
            left_pipeline,
            right_pipeline,
            merged_columns,
        )
