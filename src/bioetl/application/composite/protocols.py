"""Protocols for composite join orchestration collaborators."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.join_execution import JoinHow
    from bioetl.domain.composite.config import DependencyConfig


__all__ = [
    "DependencyJoinerProtocol",
    "JoinExecutorProtocol",
    "JoinKeyResolverProtocol",
]


@runtime_checkable
class JoinKeyResolverProtocol(Protocol):
    """Contract for resolving/normalizing join keys across pipelines."""

    def find_join_key_column(
        self,
        key: str,
        columns: list[str],
        pipeline: str | None = None,
    ) -> str | None:
        """Find best matching join column for a key.

        Args:
            key: Unqualified join key name.
            columns: Available column names in the DataFrame.
            pipeline: Optional pipeline name for qualified lookup.
        """

    def normalize_join_key_columns(
        self,
        df: pl.DataFrame,
        join_keys: list[str],
        pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Normalize selected join columns before joining.

        Args:
            df: DataFrame containing the columns to normalize.
            join_keys: List of unqualified key names to normalize.
            pipeline: Optional pipeline name for qualified column lookup.
        """

    def resolve_join_key_names(
        self,
        primary_key: str,
        seed_pipeline: str | None,
        enricher_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, str | None]:
        """Resolve join keys for seed/enricher join.

        Args:
            primary_key: Shared unqualified key name for both sides.
            seed_pipeline: Optional seed pipeline name.
            enricher_pipeline: Enricher pipeline name.
            merged_columns: Columns in the current merged DataFrame.
        """

    def resolve_join_key_names_asymmetric(
        self,
        left_key: str,
        right_key: str,
        left_pipeline: str | None,
        right_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, str | None]:
        """Resolve join keys when left/right keys have different names.

        Args:
            left_key: Unqualified key on the left side.
            right_key: Unqualified key on the right side.
            left_pipeline: Optional left-side pipeline name.
            right_pipeline: Right-side pipeline name.
            merged_columns: Columns in the current merged DataFrame.
        """

    def resolve_composite_join_keys(
        self,
        join_keys_list: list[str],
        left_pipeline: str | None,
        right_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[list[str], list[str], set[str]]:
        """Resolve join keys for multi-key dependency joins.

        Args:
            join_keys_list: List of unqualified key names to resolve.
            left_pipeline: Optional left-side pipeline name.
            right_pipeline: Right-side pipeline name.
            merged_columns: Columns in the current merged DataFrame.
        """


@runtime_checkable
class JoinExecutorProtocol(Protocol):
    """Contract for executing Polars joins."""

    def execute_polars_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_key: str,
        right_key: str,
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Execute single-key join.

        Args:
            left_df: Left-side DataFrame.
            right_df: Right-side DataFrame.
            left_key: Join column name from left_df.
            right_key: Join column name from right_df.
            pipeline_name: Pipeline name for column suffixing.
        """

    def execute_composite_key_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_keys: list[str],
        right_keys: list[str],
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Execute multi-key join.

        Args:
            left_df: Left-side DataFrame.
            right_df: Right-side DataFrame.
            left_keys: Join column names from left_df.
            right_keys: Join column names from right_df.
            pipeline_name: Pipeline name for column suffixing.
        """

    def get_polars_join_type(self) -> JoinHow:
        """Resolve join strategy to Polars join type."""


@runtime_checkable
class DependencyJoinerProtocol(Protocol):
    """Contract for dependency join orchestration logic."""

    def apply_dependency_joins(
        self,
        *,
        merged_df: pl.DataFrame,
        dependency_dfs: dict[str, pl.DataFrame],
        dependencies: Sequence[DependencyConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply configured dependency joins.

        Args:
            merged_df: Current merged DataFrame.
            dependency_dfs: Mapping from pipeline name to dependency DataFrame.
            dependencies: Dependency configurations defining join logic.
            seed_pipeline: Optional seed pipeline name for key resolution.
        """

    def apply_composite_key_dependency_join(
        self,
        *,
        merged_df: pl.DataFrame,
        dep_df: pl.DataFrame,
        dep: DependencyConfig,
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply dependency join using all composite keys.

        Args:
            merged_df: Current merged DataFrame.
            dep_df: Dependency DataFrame to join.
            dep: Dependency configuration specifying join keys.
            seed_pipeline: Optional seed pipeline name for key resolution.
        """

    def drop_system_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Drop system metadata columns from dependency DataFrame.

        Args:
            df: DataFrame from which to remove system columns.
        """
