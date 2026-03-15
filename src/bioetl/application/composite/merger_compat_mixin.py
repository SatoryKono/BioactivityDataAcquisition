"""Compatibility and delegation helpers for MergeService."""

from __future__ import annotations

from collections.abc import Sequence

import polars as pl

from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.application.composite.column_priority_orderer import (
    ColumnPriorityOrderer,
)
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.join_planner_helpers import (
    extract_base_column,
    infer_pipeline_from_table,
    infer_silver_table,
    parse_pipeline_name,
    resolve_field_aliases_from_registry,
)
from bioetl.application.composite.merger_compat_join_planner_mixin import (
    _MergeCompatibilityJoinPlannerMixin,
)
from bioetl.domain.composite.config import EnricherConfig, MergeConfig


class _MergeCompatibilityParsingMixin:
    """Legacy parsing/name helpers for merge compatibility surface."""

    _infer_silver_table = staticmethod(infer_silver_table)
    _infer_pipeline_from_table = staticmethod(infer_pipeline_from_table)
    _parse_pipeline_name = staticmethod(parse_pipeline_name)
    _get_field_aliases = staticmethod(resolve_field_aliases_from_registry)
    _extract_base_column = staticmethod(extract_base_column)


class _MergeCompatibilityConflictPolicyMixin:
    """Conflict/coalesce/priority delegation wrappers."""

    _config: MergeConfig
    _conflict_resolver: ConflictResolverService
    _coalesce_policy: CoalescePolicyService
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
        return self._coalesce_policy.coalesce_prefer_seed(df, enrichers, seed_pipeline)

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


class MergeCompatibilityMixin(
    _MergeCompatibilityParsingMixin,
    _MergeCompatibilityJoinPlannerMixin,
    _MergeCompatibilityConflictPolicyMixin,
):
    """Mixin preserving legacy MergeService helper API."""


__all__ = ["MergeCompatibilityMixin"]
