"""Unified column ordering service for composite pipelines."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import polars as pl

from bioetl.application.composite.column_orderer_group_flow import (
    apply_renames,
    order_by_yaml_groups,
)
from bioetl.application.composite.column_orderer_semantic import (
    count_groups,
    get_ordered_columns,
    group_columns,
)
from bioetl.application.composite.column_priority_orderer import get_enricher_prefix
from bioetl.application.composite.column_service_layer_filter import (
    filter_columns_by_layer_config,
)
from bioetl.application.composite.column_service_priority import (
    ColumnPriorityOrderingPolicy as ColumnPriorityOrderingPolicy,
)
from bioetl.application.composite.column_service_support import (
    collect_explicit_group_columns,
    collect_pattern_columns,
    extract_field_from_qualified_name,
    resolve_publication_field_aliases,
    sort_columns_by_provider,
)
from bioetl.application.composite.join_planner_helpers import parse_pipeline_name
from bioetl.domain.composite import (
    ColumnGroupConfig,
    EnricherConfig,
    LayerColumnConfig,
)
from bioetl.domain.ports import LoggerPort
from bioetl.domain.value_objects.column_order import (
    DEFAULT_COLUMN_ORDER,
    ColumnOrderConfig,
    SemanticGroup,
)

__all__ = [
    "ColumnOrderService",
    "collect_explicit_group_columns",
    "extract_field_from_qualified_name",
    "sort_columns_by_provider",
]


class ColumnOrderService:
    """Unified service for column ordering supporting semantic and priority strategies."""

    def __init__(
        self,
        logger: LoggerPort,
        config: ColumnOrderConfig | None = None,
        column_groups: Sequence[ColumnGroupConfig] | None = None,
        priority_orderer: ColumnPriorityOrderingPolicy | None = None,
    ) -> None:
        """Initialize unified column ordering service."""
        self._logger = logger
        self._config = config or DEFAULT_COLUMN_ORDER
        self._column_groups = tuple(column_groups) if column_groups else None
        self._priority_orderer = priority_orderer or ColumnPriorityOrderingPolicy(
            logger
        )

    def order_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Order DataFrame columns by semantic groups."""
        if not df.columns:
            return df

        if self._column_groups:
            ordered = self._order_by_yaml_groups(df.columns)
            self._logger.debug(
                "Ordered columns by YAML groups",
                total_columns=len(ordered),
                groups_configured=len(self._column_groups),
            )
        else:
            ordered = self.get_ordered_columns(df.columns)
            self._logger.debug(
                "Ordered columns by semantic groups",
                total_columns=len(ordered),
                groups_used=self._count_groups(ordered),
            )

        return df.select(ordered)

    def get_ordered_columns(self, columns: Sequence[str]) -> list[str]:
        """Get ordered column names by semantic groups."""
        return get_ordered_columns(columns, config=self._config)

    def order_column_names(self, columns: Sequence[str]) -> list[str]:
        """Order column names by semantic or YAML groups."""
        if not columns:
            return []

        if self._column_groups:
            ordered = self._order_by_yaml_groups(columns)
            self._logger.debug(
                "Ordered column names by YAML groups",
                total_columns=len(ordered),
                groups_configured=len(self._column_groups),
            )
        else:
            ordered = self.get_ordered_columns(columns)
            self._logger.debug(
                "Ordered column names by semantic groups",
                total_columns=len(ordered),
                groups_used=self._count_groups(ordered),
            )

        return ordered

    def group_columns(self, columns: Sequence[str]) -> dict[SemanticGroup, list[str]]:
        """Group columns by semantic type."""
        return group_columns(columns, config=self._config)

    def collect_field_columns(
        self,
        field: str,
        enrichers: Sequence[EnricherConfig],
        available_columns: set[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        """Collect columns matching one logical field across ordered enrichers."""
        return self._priority_orderer.collect_field_columns(
            field, enrichers, available_columns, seed_pipeline
        )

    def order_columns_by_priority(
        self,
        field: str,
        columns: list[str],
        priorities: Sequence[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        """Order columns by configured source priority."""
        return self._priority_orderer.order_columns_by_priority(
            field, columns, priorities, seed_pipeline
        )

    def filter_compatible_columns(
        self,
        df: pl.DataFrame,
        field: str,
        ordered_cols: list[str],
        can_coalesce: Callable[[pl.DataFrame, str, str], bool],
    ) -> tuple[list[str], list[str]]:
        """Filter columns to those compatible for coalescing."""
        return self._priority_orderer.filter_compatible_columns(
            df, field, ordered_cols, can_coalesce
        )

    def _count_groups(self, columns: Sequence[str]) -> dict[str, int]:
        """Count columns per semantic group."""
        return count_groups(columns, config=self._config)

    def _order_by_yaml_groups(self, columns: Sequence[str]) -> list[str]:
        """Order columns using YAML-configured groups."""
        return order_by_yaml_groups(
            columns=columns,
            column_groups=self._column_groups,
            collect_group_columns=self._collect_group_columns,
            logger=self._logger,
        )

    def _collect_group_columns(
        self,
        available: set[str],
        group: ColumnGroupConfig,
    ) -> list[str]:
        """Collect columns for a group, preserving field order from config."""
        ordered, used = collect_explicit_group_columns(
            available=available,
            group=group,
            sort_fn=self._sort_by_provider,
            extract_field_fn=self._extract_field_from_qualified,
            resolve_aliases_fn=self._field_aliases,
        )
        ordered.extend(
            collect_pattern_columns(
                available=available,
                used=used,
                group=group,
                sort_fn=self._sort_by_provider,
                logger=self._logger,
            )
        )
        return ordered

    def _sort_by_provider(
        self,
        columns: list[str],
        provider_order: tuple[str, ...],
    ) -> list[str]:
        """Sort columns by provider prefix order."""
        return sort_columns_by_provider(columns, provider_order)

    def _extract_field_from_qualified(self, column: str) -> str:
        """Extract field name from qualified column name."""
        return extract_field_from_qualified_name(column)

    def _field_aliases(self, field_name: str) -> set[str]:
        """Return compatibility aliases for evolving field names."""
        aliases, _, _ = resolve_publication_field_aliases(field_name)
        return aliases

    @staticmethod
    def _apply_renames(
        columns: list[str],
        rename_map: dict[str, str],
    ) -> list[str]:
        """Apply configured column renames through the canonical helper."""
        return apply_renames(columns, rename_map)

    def filter_by_layer_config(
        self, columns: Sequence[str], layer_config: LayerColumnConfig
    ) -> list[str]:
        """Filter columns by layer config and apply renames.

        Args:
            columns: Available column names.
            layer_config: Layer configuration with column filters and renames.

        Returns:
            Filtered and renamed column list.
        """
        return filter_columns_by_layer_config(
            columns=columns,
            layer_config=layer_config,
            column_groups=self._column_groups,
            collect_group_columns=self._collect_group_columns,
            logger=self._logger,
        )

    @staticmethod
    def _apply_renames(
        columns: list[str],
        rename_map: dict[str, str],
    ) -> list[str]:
        """Delegate legacy service-level rename calls to the focused helper."""
        return apply_renames(columns, rename_map)

    @staticmethod
    def get_enricher_prefix(enricher_pipeline: str) -> str:
        """Get enricher prefix with trailing separator."""
        return get_enricher_prefix(enricher_pipeline)

    @staticmethod
    def _parse_pipeline_name(pipeline: str) -> tuple[str, str]:
        """Parse provider_entity pipeline name into tuple."""
        return parse_pipeline_name(pipeline)
