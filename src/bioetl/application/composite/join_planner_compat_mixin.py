"""Backward-compatible join planner delegation helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite.join_execution import JoinHow
from bioetl.application.composite.protocols import (
    DependencyJoinerProtocol,
    JoinExecutorProtocol,
    JoinKeyResolverProtocol,
)
from bioetl.domain.composite.strategy import MergeStrategy

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.config import MergeConfig


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


__all__ = ["JoinPlannerCompatibilityMixin"]
