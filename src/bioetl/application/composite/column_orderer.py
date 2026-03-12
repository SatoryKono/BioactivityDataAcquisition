"""Column orderer service for composite pipelines."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from bioetl.application.composite.column_orderer_helpers import (
    collect_explicit_group_columns,
    collect_pattern_columns,
    extract_field_from_qualified_name,
    resolve_publication_field_aliases,
    sort_columns_by_provider,
)
from bioetl.application.core.publication_aliases import (
    LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE,
)
from bioetl.domain.schemas.column_order import DQ_FIELDS_SUFFIX
from bioetl.domain.value_objects.column_order import (
    DEFAULT_COLUMN_ORDER,
    ColumnOrderConfig,
    SemanticGroup,
)
from bioetl.domain.value_objects.column_qualifier import ColumnQualifier

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.config import ColumnGroupConfig, LayerColumnConfig
    from bioetl.domain.ports import LoggerPort

__all__ = ["ColumnOrdererService"]


class ColumnOrdererService:
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
        self._warned_legacy_aliases: set[str] = set()

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

        def sort_key(col: str) -> tuple[int, int, str]:
            """Sort by (group, provider_rank, column_name)."""
            group = self._config.get_group(col)
            provider_rank = self._config.get_provider_rank(col)
            field_name = ColumnQualifier.extract_field(col)
            return (group.value, provider_rank, field_name.lower())

        return sorted(columns, key=sort_key)

    def group_columns(self, columns: Sequence[str]) -> dict[SemanticGroup, list[str]]:
        """Group columns by semantic type."""
        groups: dict[SemanticGroup, list[str]] = {}

        for col in columns:
            group = self._config.get_group(col)
            if group not in groups:
                groups[group] = []
            groups[group].append(col)

        for group in groups:
            groups[group] = sorted(
                groups[group],
                key=lambda c: (
                    self._config.get_provider_rank(c),
                    ColumnQualifier.extract_field(c).lower(),
                ),
            )

        return groups

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
        counts: dict[str, int] = {}
        for col in columns:
            group = self._config.get_group(col)
            group_name = group.name
            counts[group_name] = counts.get(group_name, 0) + 1
        return counts

    def _order_by_yaml_groups(self, columns: Sequence[str]) -> list[str]:
        """Order columns using YAML-configured groups."""
        if not self._column_groups:
            return list(columns)

        all_columns = set(columns)
        ordered_columns: list[str] = []
        used_columns: set[str] = set()

        for group in self._column_groups:
            group_columns = self._collect_group_columns(
                all_columns - used_columns,
                group,
            )
            ordered_columns.extend(group_columns)
            used_columns.update(group_columns)

        dq_suffix_set = frozenset(DQ_FIELDS_SUFFIX)
        remaining = sorted(all_columns - used_columns - dq_suffix_set)
        if remaining:
            ordered_columns.extend(remaining)
            self._logger.debug(
                "Ungrouped columns added at end",
                count=len(remaining),
                sample=remaining[:5],
            )

        for dq_field in DQ_FIELDS_SUFFIX:
            if dq_field in ordered_columns:
                ordered_columns.remove(dq_field)

        for dq_field in DQ_FIELDS_SUFFIX:
            if dq_field in all_columns:
                ordered_columns.append(dq_field)

        return ordered_columns

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
        aliases, legacy_field, canonical_field = resolve_publication_field_aliases(
            field_name
        )
        if (
            legacy_field is not None
            and canonical_field is not None
            and legacy_field not in self._warned_legacy_aliases
        ):
            self._logger.warning(
                "Legacy publication field alias used on read path",
                legacy_field=legacy_field,
                canonical_field=canonical_field,
                deprecation_cutoff_date=LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE,
            )
            self._warned_legacy_aliases.add(legacy_field)

        return aliases

    def _apply_renames(
        self, columns: list[str], rename_map: dict[str, str]
    ) -> list[str]:
        """Apply column renames from rename_fields mapping."""
        return _apply_renames(columns, rename_map)

    def _filter_columns_by_explicit(
        self,
        columns: Sequence[str],
        layer_config: LayerColumnConfig,
    ) -> list[str]:
        """Apply explicit include list from layer config."""
        explicit_columns = layer_config.columns or ()
        filtered = [c for c in explicit_columns if c in columns]
        return _apply_renames(filtered, layer_config.rename_fields)

    def _filter_columns_by_groups(
        self,
        columns: Sequence[str],
        layer_config: LayerColumnConfig,
    ) -> list[str]:
        """Apply include_groups and exclude_fields filtering."""
        from fnmatch import fnmatch

        if not self._column_groups:
            self._logger.warning(
                "include_groups specified but no column_groups configured",
                include_groups=layer_config.include_groups,
            )
            return list(columns)

        include_groups = layer_config.include_groups or ()
        included_groups = [g for g in self._column_groups if g.name in include_groups]
        all_cols = set(columns)
        matched: set[str] = set()
        for group in included_groups:
            group_columns = self._collect_group_columns(all_cols - matched, group)
            matched.update(group_columns)

        if layer_config.exclude_fields:
            matched = {
                c
                for c in matched
                if not any(
                    fnmatch(c, pattern) for pattern in layer_config.exclude_fields
                )
            }

        ordered = self._order_by_yaml_groups(list(matched))
        return _apply_renames(ordered, layer_config.rename_fields)


def _apply_renames(columns: list[str], rename_map: dict[str, str]) -> list[str]:
    """Apply column renames from rename_fields mapping."""
    if not rename_map:
        return columns

    return [rename_map.get(col, col) for col in columns]
