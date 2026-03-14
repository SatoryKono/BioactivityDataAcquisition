"""Join planner compatibility mixin for MergeService facade."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import polars as pl

from bioetl.application.composite.join_planner import JoinPlannerService

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.domain.composite.config import EnricherConfig


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

    def _drop_system_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Compatibility wrapper for system-column cleanup."""
        return cast(
            pl.DataFrame,
            self._delegate_join_planner("drop_system_columns", df),
        )
