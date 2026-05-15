"""Support seams for explicit/group-based composite column ordering."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.domain.composite.config import ColumnGroupConfig

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

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


__all__ = [
    "collect_explicit_group_columns",
    "collect_pattern_columns",
    "extract_field_from_qualified_name",
    "resolve_publication_field_aliases",
    "sort_columns_by_provider",
]
