"""Compatibility and delegation helpers for MergeService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.application.composite.column_priority_orderer import (
    ColumnPriorityOrdererService,
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

if TYPE_CHECKING:
    from collections.abc import Sequence

    import polars as pl

    from bioetl.domain.composite.config import (
        EnricherConfig,
        MergeConfig,
    )


class _MergeCompatibilityParsingMixin:
    """Legacy parsing/name helpers for merge compatibility surface."""

    _config: MergeConfig

    def _infer_silver_table(self, pipeline_name: str) -> str:
        """Infer Silver table path from pipeline name."""
        return infer_silver_table(pipeline_name)

    def _infer_pipeline_from_table(self, table_path: str) -> str | None:
        """Infer pipeline name from table path (silver/provider/entity)."""
        return infer_pipeline_from_table(table_path)

    def _parse_pipeline_name(self, pipeline: str) -> tuple[str, str]:
        """Parse 'provider_entity' into (provider, entity)."""
        return parse_pipeline_name(pipeline)

    def _get_field_aliases(self, pipeline: str) -> dict[str, str] | None:
        """Get provider field alias mapping for pipeline provider."""
        return resolve_field_aliases_from_registry(pipeline)

    def _extract_base_column(self, column: str, prefix: str) -> str | None:
        """Extract base column name from prefixed column name."""
        return extract_base_column(column, prefix)


class _MergeCompatibilityConflictPolicyMixin:
    """Conflict/coalesce/priority delegation wrappers."""

    _config: MergeConfig
    _conflict_resolver: ConflictResolverService
    _coalesce_policy: CoalescePolicyService
    _priority_orderer: ColumnPriorityOrdererService

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

    def _can_coalesce(self, df: pl.DataFrame, col1: str, col2: str) -> bool:
        """Compatibility wrapper for type-compatibility checks."""
        return self._coalesce_policy.can_coalesce(df, col1, col2)

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

    def _coalesce_first_non_null(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for first-non-null coalesce policy."""
        return self._coalesce_policy.coalesce_first_non_null(
            df,
            enrichers,
            seed_pipeline,
        )

    def _collect_field_columns(
        self,
        field: str,
        enrichers: Sequence[EnricherConfig],
        available_columns: set[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        """Compatibility wrapper for field-column collection."""
        return self._priority_orderer.collect_field_columns(
            field,
            enrichers,
            available_columns,
            seed_pipeline,
        )

    def _order_columns_by_priority(
        self,
        field: str,
        columns: list[str],
        priorities: Sequence[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        """Compatibility wrapper for source-priority ordering."""
        return self._priority_orderer.order_columns_by_priority(
            field,
            columns,
            priorities,
            seed_pipeline,
        )

    def _filter_compatible_columns(
        self,
        df: pl.DataFrame,
        field: str,
        ordered_cols: list[str],
    ) -> tuple[list[str], list[str]]:
        """Compatibility wrapper for explicit-rule compatibility filtering."""
        return self._priority_orderer.filter_compatible_columns(
            df,
            field,
            ordered_cols,
            self._coalesce_policy.can_coalesce,
        )

    def _apply_explicit_rules(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for explicit priority rules."""
        return self._coalesce_policy.apply_explicit_rules(
            df,
            enrichers,
            self._config.field_priorities,
            seed_pipeline,
        )


class MergeCompatibilityMixin(
    _MergeCompatibilityParsingMixin,
    _MergeCompatibilityJoinPlannerMixin,
    _MergeCompatibilityConflictPolicyMixin,
):
    """Mixin preserving legacy MergeService helper API."""


__all__ = ["MergeCompatibilityMixin"]
