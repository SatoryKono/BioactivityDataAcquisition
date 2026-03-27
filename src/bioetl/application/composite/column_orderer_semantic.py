"""Pure semantic ordering helpers for composite column ordering."""

from __future__ import annotations

__all__ = ["count_groups", "get_ordered_columns", "group_columns"]

from collections.abc import Sequence

from bioetl.domain.value_objects.column_order import (
    ColumnOrderConfig,
    SemanticGroup,
)
from bioetl.domain.value_objects.column_qualifier import ColumnQualifier


def get_ordered_columns(
    columns: Sequence[str],
    *,
    config: ColumnOrderConfig,
) -> list[str]:
    """Get columns in semantic order."""

    def sort_key(col: str) -> tuple[int, int, str]:
        group = config.get_group(col)
        provider_rank = config.get_provider_rank(col)
        field_name = ColumnQualifier.extract_field(col)
        return (group.value, provider_rank, field_name.lower())

    return sorted(columns, key=sort_key)


def group_columns(
    columns: Sequence[str],
    *,
    config: ColumnOrderConfig,
) -> dict[SemanticGroup, list[str]]:
    """Group columns by semantic type."""
    groups: dict[SemanticGroup, list[str]] = {}

    for col in columns:
        group = config.get_group(col)
        groups.setdefault(group, []).append(col)

    for group, items in groups.items():
        groups[group] = sorted(
            items,
            key=lambda c: (
                config.get_provider_rank(c),
                ColumnQualifier.extract_field(c).lower(),
            ),
        )

    return groups


def count_groups(
    columns: Sequence[str],
    *,
    config: ColumnOrderConfig,
) -> dict[str, int]:
    """Count columns per semantic group."""
    counts: dict[str, int] = {}
    for col in columns:
        group_name = config.get_group(col).name
        counts[group_name] = counts.get(group_name, 0) + 1
    return counts
