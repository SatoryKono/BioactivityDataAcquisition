"""Column orderer service for composite pipelines."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from bioetl.application.composite.column_orderer_group_flow import (
    apply_renames,
    filter_columns_by_explicit,
    filter_columns_by_groups,
    order_by_yaml_groups,
)
from bioetl.application.composite.column_orderer_helpers import (
    collect_explicit_group_columns,
    collect_pattern_columns,
    extract_field_from_qualified_name,
    resolve_publication_field_aliases,
    sort_columns_by_provider,
)
from bioetl.application.composite.column_orderer_semantic import (
    count_groups,
    get_ordered_columns,
    group_columns,
)
from bioetl.domain.value_objects.column_order import (
    DEFAULT_COLUMN_ORDER,
    ColumnOrderConfig,
    SemanticGroup,
)

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.config import ColumnGroupConfig, LayerColumnConfig
    from bioetl.domain.ports import LoggerPort

__all__ = ["ColumnOrderer"]


class ColumnOrderer:
    """Service for ordering columns by semantic groups."""

    def __init__(
        self,
        logger: LoggerPort,
        config: ColumnOrderConfig | None = None,
        column_groups: Sequence[ColumnGroupConfig] | None = None,
    ) -> None:
        """Initialize orderer."""
        self._logger = logger
        self._config = config or DEFAULT_COLUMN_ORDER
        self._column_groups = tuple(column_groups) if column_groups else None

    # === Public API ===

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

    def order_column_names(self, columns: Sequence[str]) -> list[str]:
        """Order column names by semantic groups."""
        if not columns:
            return []

        if self._column_groups:
            return self._order_by_yaml_groups(columns)

        return self.get_ordered_columns(columns)

    def get_ordered_columns(self, columns: Sequence[str]) -> list[str]:
        """Get columns in semantic order."""
        return get_ordered_columns(columns, config=self._config)

    def group_columns(self, columns: Sequence[str]) -> dict[SemanticGroup, list[str]]:
        """Group columns by semantic type."""
        return group_columns(columns, config=self._config)

    def filter_by_layer_config(
        self,
        columns: Sequence[str],
        layer_config: LayerColumnConfig,
    ) -> list[str]:
        """Filter columns by layer-specific configuration."""
        if layer_config.columns:
            return self._filter_columns_by_explicit(columns, layer_config)

        if layer_config.include_groups:
            return self._filter_columns_by_groups(columns, layer_config)

        return list(columns)

    # === Internal helpers ===

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
                available, used, group, self._sort_by_provider, self._logger
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

    def _apply_renames(
        self, columns: list[str], rename_map: dict[str, str]
    ) -> list[str]:
        """Apply column renames from rename_fields mapping."""
        return apply_renames(columns, rename_map)

    def _filter_columns_by_explicit(
        self,
        columns: Sequence[str],
        layer_config: LayerColumnConfig,
    ) -> list[str]:
        """Apply explicit include list from layer config."""
        return filter_columns_by_explicit(
            columns=columns,
            layer_config=layer_config,
        )

    def _filter_columns_by_groups(
        self,
        columns: Sequence[str],
        layer_config: LayerColumnConfig,
    ) -> list[str]:
        """Apply include_groups and exclude_fields filtering."""
        return filter_columns_by_groups(
            columns=columns,
            layer_config=layer_config,
            column_groups=self._column_groups,
            collect_group_columns=self._collect_group_columns,
            logger=self._logger,
        )
