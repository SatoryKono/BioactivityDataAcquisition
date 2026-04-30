"""Unified column ordering service for composite pipelines."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

import polars as pl

from bioetl.application.composite.column_orderer_group_flow import (
    apply_renames,
    filter_columns_by_explicit,
    filter_columns_by_groups,
    order_by_yaml_groups,
)
from bioetl.application.composite.column_orderer_semantic import (
    count_groups,
    get_ordered_columns,
    group_columns,
)
from bioetl.application.composite.column_priority_orderer import (
    collect_priority_field_columns,
    get_enricher_prefix,
    order_priority_columns,
)
from bioetl.application.composite.join_planner_helpers import parse_pipeline_name
from bioetl.domain.composite.config import (
    ColumnGroupConfig,
    EnricherConfig,
    LayerColumnConfig,
)
from bioetl.domain.value_objects.column_order import (
    DEFAULT_COLUMN_ORDER,
    ColumnOrderConfig,
    SemanticGroup,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
__all__ = ["ColumnOrderService"]
_SortFn = Callable[[list[str], tuple[str, ...]], list[str]]


def sort_columns_by_provider(
    columns: list[str],
    provider_order: tuple[str, ...],
) -> list[str]:
    """Sort columns by provider prefix order."""
    order_map = {provider: idx + 1 for idx, provider in enumerate(provider_order)}
    max_idx = len(provider_order) + 1

    def sort_key(col: str) -> tuple[int, str]:
        """Return ``(provider_index, name)`` placing seed columns first."""
        parts = col.split(".", maxsplit=2)
        if len(parts) < 3:
            return (0, col.lower())

        provider = parts[0].lower()
        return (order_map.get(provider, max_idx), col.lower())

    return sorted(columns, key=sort_key)


def extract_field_from_qualified_name(column: str) -> str:
    """Extract field name from a qualified column name."""
    parts = column.split(".", maxsplit=3)
    if len(parts) == 3:
        return parts[2]
    if len(parts) == 2:
        return parts[1]
    return column


def resolve_publication_field_aliases(
    field_name: str,
) -> tuple[set[str], str | None, str | None]:
    """Return alias set plus optional legacy/canonical mapping for warnings."""
    return {field_name}, None, None


def collect_pattern_columns(
    available: set[str],
    used: set[str],
    group: ColumnGroupConfig,
    sort_fn: _SortFn,
    logger: LoggerPort,
) -> list[str]:
    """Collect columns matching a group regex pattern."""
    if not group.pattern:
        return []
    try:
        pattern_re = re.compile(group.pattern, re.IGNORECASE)
    except re.error as error:
        logger.warning(
            "Invalid regex pattern in column group",
            group=group.name,
            pattern=group.pattern,
            error=str(error),
        )
        return []

    pattern_matches: list[str] = []
    for column in available:
        if column not in used and pattern_re.search(column):
            pattern_matches.append(column)
            used.add(column)
    return sort_fn(pattern_matches, group.provider_order)


def collect_explicit_group_columns(
    available: set[str],
    group: ColumnGroupConfig,
    sort_fn: _SortFn,
    extract_field_fn: Callable[[str], str],
    resolve_aliases_fn: Callable[[str], set[str]],
) -> tuple[list[str], set[str]]:
    """Collect explicit field matches for a YAML group in declared field order."""
    available_list = list(available)
    col_order = {col: i for i, col in enumerate(available_list)}
    field_to_cols = _index_columns_by_field(
        available_list=available_list,
        extract_field_fn=extract_field_fn,
    )

    return _collect_group_field_columns(
        group=group,
        field_to_cols=field_to_cols,
        col_order=col_order,
        sort_fn=sort_fn,
        resolve_aliases_fn=resolve_aliases_fn,
    )


def _collect_group_field_columns(
    *,
    group: ColumnGroupConfig,
    field_to_cols: dict[str, list[str]],
    col_order: dict[str, int],
    sort_fn: _SortFn,
    resolve_aliases_fn: Callable[[str], set[str]],
) -> tuple[list[str], set[str]]:
    """Collect group fields while preserving declaration order and de-duplication."""
    ordered: list[str] = []
    used: set[str] = set()

    for field_name in group.fields:
        ordered.extend(
            _collect_ordered_field_matches(
                field_name=field_name,
                group=group,
                field_to_cols=field_to_cols,
                col_order=col_order,
                sort_fn=sort_fn,
                resolve_aliases_fn=resolve_aliases_fn,
                used=used,
            )
        )

    return ordered, used


def _collect_ordered_field_matches(
    *,
    field_name: str,
    group: ColumnGroupConfig,
    field_to_cols: dict[str, list[str]],
    col_order: dict[str, int],
    sort_fn: _SortFn,
    resolve_aliases_fn: Callable[[str], set[str]],
    used: set[str],
) -> list[str]:
    """Collect one field's matches, then normalize ordering inside that field."""
    field_matches = _collect_alias_matches(
        field_to_cols=field_to_cols,
        aliases=resolve_aliases_fn(field_name),
        used=used,
    )
    field_matches.sort(key=lambda c: col_order[c])
    return sort_fn(field_matches, group.provider_order)


def _index_columns_by_field(
    *,
    available_list: list[str],
    extract_field_fn: Callable[[str], str],
) -> dict[str, list[str]]:
    """Index available columns by extracted field name and exact fallback."""
    field_to_cols: dict[str, list[str]] = {}
    for col in available_list:
        extracted = extract_field_fn(col)
        field_to_cols.setdefault(extracted, []).append(col)
        if extracted != col:
            field_to_cols.setdefault(col, []).append(col)
    return field_to_cols


def _collect_alias_matches(
    *,
    field_to_cols: dict[str, list[str]],
    aliases: set[str],
    used: set[str],
) -> list[str]:
    """Collect unused columns matching any alias in declared field order."""
    matches: list[str] = []
    for alias in aliases:
        for col in field_to_cols.get(alias, []):
            if col in used:
                continue
            matches.append(col)
            used.add(col)
    return matches


class _ColumnPriorityOrderingStrategy:
    """Internal non-deprecated strategy for explicit source-priority ordering."""

    def __init__(self, logger: LoggerPort) -> None:
        self._logger = logger

    def collect_field_columns(
        self,
        field: str,
        enrichers: Sequence[EnricherConfig],
        available_columns: set[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        columns, used_parse_fallback = collect_priority_field_columns(
            field=field,
            enrichers=enrichers,
            available_columns=available_columns,
            seed_pipeline=seed_pipeline,
        )
        if used_parse_fallback and seed_pipeline:
            self._logger.debug(
                "Could not parse seed pipeline for field collection",
                seed_pipeline=seed_pipeline,
                field=field,
            )
        return columns

    def order_columns_by_priority(
        self,
        field: str,
        columns: list[str],
        priorities: Sequence[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        ordered_cols, used_parse_fallback = order_priority_columns(
            field=field,
            columns=columns,
            priorities=priorities,
            seed_pipeline=seed_pipeline,
        )
        if used_parse_fallback and seed_pipeline:
            self._logger.debug(
                "Could not parse seed pipeline for priority ordering",
                seed_pipeline=seed_pipeline,
                field=field,
            )
        return ordered_cols

    def filter_compatible_columns(
        self,
        df: pl.DataFrame,
        field: str,
        ordered_cols: list[str],
        can_coalesce: Callable[[pl.DataFrame, str, str], bool],
    ) -> tuple[list[str], list[str]]:
        if not ordered_cols:
            return [], []

        base_col = ordered_cols[0]
        compatible_cols = [base_col]
        incompatible_cols: list[str] = []

        for col in ordered_cols[1:]:
            if can_coalesce(df, base_col, col):
                compatible_cols.append(col)
                continue
            self._logger.debug(
                "Skipping column with incompatible type in explicit rules",
                field=field,
                incompatible_col=col,
                base_type=str(df[base_col].dtype),
                col_type=str(df[col].dtype),
            )
            incompatible_cols.append(col)

        return compatible_cols, incompatible_cols

    @staticmethod
    def get_enricher_prefix(enricher_pipeline: str) -> str:
        """Expose legacy prefix helper for compatibility call sites."""
        return get_enricher_prefix(enricher_pipeline)


class ColumnOrderService:
    """Unified service for column ordering supporting semantic and priority strategies."""

    def __init__(
        self,
        logger: LoggerPort,
        config: ColumnOrderConfig | None = None,
        column_groups: Sequence[ColumnGroupConfig] | None = None,
        priority_orderer: _ColumnPriorityOrderingStrategy | None = None,
    ) -> None:
        """Initialize unified column ordering service."""
        self._logger = logger
        self._config = config or DEFAULT_COLUMN_ORDER
        self._column_groups = tuple(column_groups) if column_groups else None
        self._priority_orderer = priority_orderer or _ColumnPriorityOrderingStrategy(
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

    def collect_field_columns(
        self,
        field: str,
        enrichers: Sequence[EnricherConfig],
        available_columns: set[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        """Collect all qualified/legacy columns for a field from all sources."""
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

    @staticmethod
    def get_enricher_prefix(enricher_pipeline: str) -> str:
        """Get enricher prefix with trailing separator."""
        return get_enricher_prefix(enricher_pipeline)

    @staticmethod
    def _parse_pipeline_name(pipeline: str) -> tuple[str, str]:
        """Parse provider_entity pipeline name into tuple."""
        return parse_pipeline_name(pipeline)
