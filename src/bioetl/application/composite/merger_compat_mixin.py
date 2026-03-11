"""Compatibility and delegation helpers for MergeService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.application.composite.column_priority_orderer import (
    ColumnPriorityOrdererService,
)
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.join_planner_helpers import parse_pipeline_name
from bioetl.application.composite.merger_compat_join_planner_mixin import (
    _MergeCompatibilityJoinPlannerMixin,
)
from bioetl.domain.registry.field_aliases import get_alias_map_for_provider

if TYPE_CHECKING:
    from collections.abc import Sequence

    import polars as pl

    from bioetl.domain.composite.config import (
        EnricherConfig,
        MergeConfig,
    )


def _path_to_table_name_local(path: str) -> str:
    """Convert a full path to a table name by stripping layer prefix."""
    normalized = path.replace("\\", "/")

    for layer in ("silver/", "gold/", "bronze/"):
        if layer in normalized:
            idx = normalized.find(layer)
            return normalized[idx + len(layer) :]

    return path


class _MergeCompatibilityParsingMixin:
    """Legacy parsing/name helpers for merge compatibility surface."""

    _config: MergeConfig

    def _infer_silver_table(self, pipeline_name: str) -> str:
        """Infer Silver table path from pipeline name."""
        parts = pipeline_name.split("_", 1)
        if len(parts) == 2:
            provider, entity = parts
            return f"silver/{provider}/{entity}"
        return f"silver/{pipeline_name}"

    def _infer_pipeline_from_table(self, table_path: str) -> str | None:
        """Infer pipeline name from table path (silver/provider/entity)."""
        normalized = table_path.replace("\\", "/")
        has_layer = any(
            layer in normalized for layer in ("silver/", "gold/", "bronze/")
        )
        if not has_layer:
            return None

        table_name = _path_to_table_name_local(table_path)
        parts = table_name.split("/")
        if len(parts) == 2:
            return f"{parts[0]}_{parts[1]}"
        return None

    def _parse_pipeline_name(self, pipeline: str) -> tuple[str, str]:
        """Parse 'provider_entity' into (provider, entity)."""
        return parse_pipeline_name(pipeline)

    def _get_field_aliases(self, pipeline: str) -> dict[str, str] | None:
        """Get provider field alias mapping for pipeline provider."""
        try:
            provider, _entity = self._parse_pipeline_name(pipeline)
        except ValueError:
            return None
        alias_map = get_alias_map_for_provider(provider)
        return alias_map if alias_map else None

    def _extract_base_column(self, column: str, prefix: str) -> str | None:
        """Extract base column name from prefixed column name."""
        if column.startswith(prefix):
            return column[len(prefix) :]
        return None


class _MergeCompatibilityConflictPolicyMixin:
    """Conflict/coalesce/priority delegation wrappers."""

    _config: MergeConfig
    _conflict_resolver: ConflictResolverService
    _coalesce_policy: CoalescePolicyService
    _priority_orderer: ColumnPriorityOrdererService

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
