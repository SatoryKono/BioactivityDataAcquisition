"""Join planner compatibility mixin for MergeService facade."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import polars as pl

from bioetl.application.composite.join_planner import JoinHow, JoinPlannerService

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.domain.composite.config import DependencyConfig, EnricherConfig


class _MergeCompatibilityJoinPlannerMixin:
    """Join-planner delegation wrappers preserved for compatibility."""

    _join_planner: JoinPlannerService

    def _delegate_join_planner(
        self,
        method_name: str,
        *args: object,
    ) -> (
        Any
    ):  # Any: dynamic bridge preserves typed legacy wrappers over service dispatch
        """Route sync compatibility wrappers to the canonical join planner."""
        method = cast(
            Any,  # Any: getattr-based dispatch returns heterogeneous join-planner callables
            getattr(self._join_planner, method_name),
        )
        return method(*args)

    async def _delegate_join_planner_async(
        self,
        method_name: str,
        *args: object,
        **kwargs: object,
    ) -> Any:  # Any: async bridge preserves typed legacy wrappers over service dispatch
        """Route async compatibility wrappers to the canonical join planner."""
        method = cast(
            Any,  # Any: getattr-based dispatch returns heterogeneous async callables
            getattr(self._join_planner, method_name),
        )
        return await method(*args, **kwargs)

    def _find_join_key_column(
        self,
        key: str,
        columns: list[str],
        pipeline: str | None = None,
    ) -> str | None:
        """Compatibility wrapper for join-key column lookup."""
        return cast(
            str | None,
            self._delegate_join_planner(
                "find_join_key_column",
                key,
                columns,
                pipeline,
            ),
        )

    def _normalize_join_key_columns(
        self,
        df: pl.DataFrame,
        join_keys: list[str],
        pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for join-key normalization."""
        return cast(
            pl.DataFrame,
            self._delegate_join_planner(
                "normalize_join_key_columns",
                df,
                join_keys,
                pipeline,
            ),
        )

    async def _apply_joins(
        self,
        seed_df: pl.DataFrame,
        enricher_dfs: dict[str, pl.DataFrame],
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for enricher joins."""
        return cast(
            pl.DataFrame,
            await self._delegate_join_planner_async(
                "apply_joins",
                seed_df=seed_df,
                enricher_dfs=enricher_dfs,
                enrichers=enrichers,
                seed_pipeline=seed_pipeline,
            ),
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
        return cast(
            pl.DataFrame,
            self._delegate_join_planner(
                "execute_polars_join",
                left_df,
                right_df,
                left_key,
                right_key,
                pipeline_name,
            ),
        )

    async def _apply_dependency_joins(
        self,
        merged_df: pl.DataFrame,
        dependency_dfs: dict[str, pl.DataFrame],
        dependencies: Sequence[DependencyConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for dependency joins."""
        return cast(
            pl.DataFrame,
            await self._delegate_join_planner_async(
                "apply_dependency_joins",
                merged_df=merged_df,
                dependency_dfs=dependency_dfs,
                dependencies=dependencies,
                seed_pipeline=seed_pipeline,
            ),
        )

    def _resolve_composite_join_keys(
        self,
        join_keys_list: list[str],
        left_pipeline: str | None,
        right_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[list[str], list[str], set[str]]:
        """Compatibility wrapper for composite join-key resolution."""
        return cast(
            tuple[list[str], list[str], set[str]],
            self._delegate_join_planner(
                "resolve_composite_join_keys",
                join_keys_list,
                left_pipeline,
                right_pipeline,
                merged_columns,
            ),
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
        return cast(
            pl.DataFrame,
            self._delegate_join_planner(
                "execute_composite_key_join",
                left_df,
                right_df,
                left_keys,
                right_keys,
                pipeline_name,
            ),
        )

    def _apply_composite_key_dependency_join(
        self,
        merged_df: pl.DataFrame,
        dep_df: pl.DataFrame,
        dep: DependencyConfig,
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for composite-key dependency joins."""
        return cast(
            pl.DataFrame,
            self._delegate_join_planner(
                "apply_composite_key_dependency_join",
                merged_df,
                dep_df,
                dep,
                seed_pipeline,
            ),
        )

    def _get_polars_join_type(self) -> JoinHow:
        """Compatibility wrapper for join strategy mapping."""
        return cast(JoinHow, self._delegate_join_planner("get_polars_join_type"))

    def _drop_system_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Compatibility wrapper for system-column cleanup."""
        return cast(
            pl.DataFrame,
            self._delegate_join_planner("drop_system_columns", df),
        )

    def _resolve_join_key_names(
        self,
        primary_key: str,
        seed_pipeline: str | None,
        enricher_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, str | None]:
        """Compatibility wrapper for symmetric join-key resolution."""
        return cast(
            tuple[str, str, str | None],
            self._delegate_join_planner(
                "resolve_join_key_names",
                primary_key,
                seed_pipeline,
                enricher_pipeline,
                merged_columns,
            ),
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
        return cast(
            tuple[str, str, str | None],
            self._delegate_join_planner(
                "resolve_join_key_names_asymmetric",
                left_key,
                right_key,
                left_pipeline,
                right_pipeline,
                merged_columns,
            ),
        )
