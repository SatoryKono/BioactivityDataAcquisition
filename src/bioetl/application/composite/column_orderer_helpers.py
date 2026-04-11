"""Pure helper functions for column ordering."""

from __future__ import annotations

import re
from collections.abc import Callable

from bioetl.domain.composite.config import ColumnGroupConfig
from bioetl.domain.ports import LoggerPort

_SortFn = Callable[[list[str], tuple[str, ...]], list[str]]

__all__ = [
    "collect_explicit_group_columns",
    "collect_pattern_columns",
    "extract_field_from_qualified_name",
    "resolve_publication_field_aliases",
    "sort_columns_by_provider",
]


def sort_columns_by_provider(
    columns: list[str],
    provider_order: tuple[str, ...],
) -> list[str]:
    """Sort columns by provider prefix order."""
    # ⚡ Bolt: Pre-compute O(1) provider lookup dictionary to avoid O(N) .index() calls
    provider_lookup = {p: i for i, p in enumerate(provider_order)}
    fallback_index = len(provider_order) + 1

    def sort_key(col: str) -> tuple[int, str]:
        """Return (provider_index, name) placing seed columns first."""
        # ⚡ Bolt: Bounded split to limit list allocation overhead
        parts = col.split(".", maxsplit=2)
        if len(parts) < 3:
            return (0, col.lower())

        provider = parts[0].lower()
        idx = provider_lookup.get(provider)
        if idx is not None:
            return (idx + 1, col.lower())
        return (fallback_index, col.lower())

    return sorted(columns, key=sort_key)


def extract_field_from_qualified_name(column: str) -> str:
    """Extract field name from qualified column name."""
    # ⚡ Bolt: safely limit list allocation overhead by using .split('.', maxsplit=3)
    # while fully preserving exactly 2 or 3 parts behavior
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
    except re.error as e:
        logger.warning(
            "Invalid regex pattern in column group",
            group=group.name,
            pattern=group.pattern,
            error=str(e),
        )
        return []

    pattern_matches: list[str] = []
    for col in available:
        if col not in used and pattern_re.search(col):
            pattern_matches.append(col)
            used.add(col)
    return sort_fn(pattern_matches, group.provider_order)


def collect_explicit_group_columns(
    available: set[str],
    group: ColumnGroupConfig,
    sort_fn: _SortFn,
    extract_field_fn: Callable[[str], str],
    resolve_aliases_fn: Callable[[str], set[str]],
) -> tuple[list[str], set[str]]:
    """Collect explicit field matches for a YAML group in declared field order."""
    ordered: list[str] = []
    used: set[str] = set()

    # ⚡ Bolt: Hoist redundant extract_field_fn calls out of the inner loop
    # Pre-computing this dictionary changes the execution time from O(N * M) to O(N)
    extracted_fields = {col: extract_field_fn(col) for col in available}

    for field_name in group.fields:
        field_matches: list[str] = []
        aliases = resolve_aliases_fn(field_name)
        for col in available:
            if col in used:
                continue
            extracted = extracted_fields[col]
            if extracted in aliases or col in aliases:
                field_matches.append(col)
                used.add(col)
        ordered.extend(sort_fn(field_matches, group.provider_order))

    return ordered, used
