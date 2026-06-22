"""YAML-group ordering helpers for :mod:`bioetl.application.composite.column_orderer`."""

from __future__ import annotations

__all__ = [
    "apply_renames",
    "filter_columns_by_explicit",
    "filter_columns_by_groups",
    "order_by_yaml_groups",
]

from collections.abc import Callable, Sequence
from fnmatch import fnmatch

from bioetl.domain.composite import ColumnGroupConfig, LayerColumnConfig
from bioetl.domain.ports import LoggerPort
from bioetl.domain.schemas.column_order import DQ_FIELDS_SUFFIX


def order_by_yaml_groups(
    *,
    columns: Sequence[str],
    column_groups: Sequence[ColumnGroupConfig] | None,
    collect_group_columns: Callable[[set[str], ColumnGroupConfig], list[str]],
    logger: LoggerPort,
) -> list[str]:
    """Order columns using YAML-configured groups."""
    if not column_groups:
        return list(columns)

    all_columns = set(columns)
    ordered_columns: list[str] = []
    used_columns: set[str] = set()

    for group in column_groups:
        group_columns = collect_group_columns(
            all_columns - used_columns,
            group,
        )
        ordered_columns.extend(group_columns)
        used_columns.update(group_columns)

    dq_suffix_set = frozenset(DQ_FIELDS_SUFFIX)
    remaining = sorted(all_columns - used_columns - dq_suffix_set)
    if remaining:
        ordered_columns.extend(remaining)
        logger.debug(
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


def apply_renames(columns: list[str], rename_map: dict[str, str]) -> list[str]:
    """Apply column renames from rename_fields mapping."""
    if not rename_map:
        return columns
    return [rename_map.get(col, col) for col in columns]


def filter_columns_by_explicit(
    *,
    columns: Sequence[str],
    layer_config: LayerColumnConfig,
) -> list[str]:
    """Apply explicit include list from layer config."""
    explicit_columns = layer_config.columns or ()
    filtered = [column for column in explicit_columns if column in columns]
    return apply_renames(filtered, layer_config.rename_fields)


def filter_columns_by_groups(
    *,
    columns: Sequence[str],
    layer_config: LayerColumnConfig,
    column_groups: Sequence[ColumnGroupConfig] | None,
    collect_group_columns: Callable[[set[str], ColumnGroupConfig], list[str]],
    logger: LoggerPort,
) -> list[str]:
    """Apply include_groups and exclude_fields filtering."""
    if not column_groups:
        logger.warning(
            "include_groups specified but no column_groups configured",
            include_groups=layer_config.include_groups,
        )
        return list(columns)

    include_groups = layer_config.include_groups or ()
    included_groups = [group for group in column_groups if group.name in include_groups]
    all_cols = set(columns)
    matched: set[str] = set()
    for group in included_groups:
        group_columns = collect_group_columns(all_cols - matched, group)
        matched.update(group_columns)

    if layer_config.exclude_fields:
        matched = {
            column
            for column in matched
            if not any(
                fnmatch(column, pattern) for pattern in layer_config.exclude_fields
            )
        }

    ordered = order_by_yaml_groups(
        columns=list(matched),
        column_groups=column_groups,
        collect_group_columns=collect_group_columns,
        logger=logger,
    )
    return apply_renames(ordered, layer_config.rename_fields)
