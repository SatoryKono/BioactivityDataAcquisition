# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Delegating API surface for ``JoinPlannerService``."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.composite.join_execution import JoinHow

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.protocols import (
        DependencyJoinerProtocol,
        JoinExecutorProtocol,
        JoinKeyResolverProtocol,
    )
    from bioetl.domain.composite import DependencyConfig


class JoinPlannerDelegationMixin:
    """Keep the planner facade thin by delegating focused operations."""

    _join_key_resolver: JoinKeyResolverProtocol = cast(
        Any, None
    )  # Any: host default (PD4)
    _dependency_joiner: DependencyJoinerProtocol = cast(
        Any, None
    )  # Any: host default (PD4)
    _join_executor: JoinExecutorProtocol = cast(Any, None)  # Any: host default (PD4)

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

    async def apply_dependency_joins(
        self,
        merged_df: pl.DataFrame,
        dependency_dfs: dict[str, pl.DataFrame],
        dependencies: Sequence[DependencyConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply configured dependency joins to merged DataFrame."""
        await asyncio.sleep(0)
        return self._dependency_joiner.apply_dependency_joins(
            merged_df=merged_df,
            dependency_dfs=dependency_dfs,
            dependencies=list(dependencies),
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
