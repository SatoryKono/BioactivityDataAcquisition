"""Protocols for composite pipeline orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.join_execution import JoinHow
    from bioetl.domain.composite import DependencyConfig

__all__ = [
    "DependencyJoinerProtocol",
    "JoinExecutorProtocol",
    "JoinKeyResolverProtocol",
]


@runtime_checkable
class JoinKeyResolverProtocol(Protocol):
    """Protocol for resolving and normalizing join-key column names."""

    def find_join_key_column(
        self,
        key: str,
        columns: list[str],
        pipeline: str | None = None,
    ) -> str | None:
        """Find a matching join-key column."""
        ...

    def normalize_join_key_columns(
        self,
        df: pl.DataFrame,
        join_keys: list[str],
        pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Normalize join-key columns before joining."""
        ...

    def resolve_join_key_names(
        self,
        primary_key: str,
        seed_pipeline: str | None,
        enricher_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, str | None]:
        """Resolve single-key join column names."""
        ...

    def resolve_join_key_names_asymmetric(
        self,
        left_key: str,
        right_key: str,
        left_pipeline: str | None,
        right_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, str | None]:
        """Resolve join column names when left/right keys differ."""
        ...

    def resolve_composite_join_keys(
        self,
        join_keys_list: list[str],
        left_pipeline: str | None,
        right_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[list[str], list[str], set[str]]:
        """Resolve composite-key join column names."""
        ...


@runtime_checkable
class JoinExecutorProtocol(Protocol):
    """Protocol for executing physical dataframe joins."""

    def get_polars_join_type(self) -> JoinHow:
        """Resolve current join type."""
        ...

    def execute_polars_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_key: str,
        right_key: str,
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Execute single-key join."""
        ...

    def execute_composite_key_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_keys: list[str],
        right_keys: list[str],
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Execute multi-key join."""
        ...


@runtime_checkable
class DependencyJoinerProtocol(Protocol):
    """Protocol for dependency-specific join orchestration."""

    def apply_dependency_joins(
        self,
        *,
        merged_df: pl.DataFrame,
        dependency_dfs: dict[str, pl.DataFrame],
        dependencies: list[DependencyConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply all configured dependency joins."""
        ...

    def apply_composite_key_dependency_join(
        self,
        *,
        merged_df: pl.DataFrame,
        dep_df: pl.DataFrame,
        dep: DependencyConfig,
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply a composite-key dependency join."""
        ...

    def drop_system_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Drop system columns from dependency/enricher frames."""
        ...
