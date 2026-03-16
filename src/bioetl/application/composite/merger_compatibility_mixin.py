"""Compatibility helper methods preserved on ``MergeService`` during RF-005."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

import polars as pl

if TYPE_CHECKING:
    from bioetl.application.composite.coalesce_policy import CoalescePolicyService
    from bioetl.application.composite.column_priority_orderer import (
        ColumnPriorityOrderer,
    )
    from bioetl.application.composite.conflict_resolver import ConflictResolverService
    from bioetl.application.composite.join_planner import JoinPlannerService
    from bioetl.domain.composite.config import EnricherConfig


class MergeCompatibilityMixin:
    """Keep test-facing compatibility wrappers off the core merge orchestrator."""

    _coalesce_policy: CoalescePolicyService
    _conflict_resolver: ConflictResolverService
    _join_planner: JoinPlannerService
    _priority_orderer: ColumnPriorityOrderer

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

    def _extract_field_from_qualified(self, column: str) -> str:
        """Extract field name from qualified column (x.y.z -> z)."""
        return self._coalesce_policy.extract_field_from_qualified(column)

    def _get_enricher_prefix(
        self,
        enricher_pipeline: str,
        seed_pipeline: str | None = None,
    ) -> str:
        """Compatibility helper for enricher prefix resolution."""
        _ = seed_pipeline
        return self._priority_orderer.get_enricher_prefix(enricher_pipeline)

    def _resolve_conflicts(
        self,
        df: pl.DataFrame,
        enricher_dfs: dict[str, pl.DataFrame],
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for policy-based conflict resolution."""
        return self._conflict_resolver.resolve_conflicts(
            df,
            enricher_dfs,
            enrichers,
            seed_pipeline,
        )

    def _coalesce_prefer_seed(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for seed-priority coalesce policy."""
        return self._coalesce_policy.coalesce_prefer_seed(
            df,
            enrichers,
            seed_pipeline,
        )

    def _coalesce_prefer_enricher(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for enricher-priority coalesce policy."""
        return self._coalesce_policy.coalesce_prefer_enricher(
            df,
            enrichers,
            seed_pipeline,
        )

    def _delegate_join_planner(
        self,
        method_name: str,
        *args: object,
    ) -> (
        Any
    ):  # Any: getattr-based dispatch returns heterogeneous join-planner callables
        """Route sync helper calls to the canonical join planner."""
        method = cast(
            Any,  # Any: dynamic bridge preserves typed wrappers over service dispatch
            getattr(self._join_planner, method_name),
        )
        return method(*args)

    async def _delegate_join_planner_async(
        self,
        method_name: str,
        *args: object,
        **kwargs: object,
    ) -> Any:  # Any: getattr-based dispatch returns heterogeneous async callables
        """Route async helper calls to the canonical join planner."""
        method = cast(
            Any,  # Any: dynamic bridge preserves typed wrappers over service dispatch
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
