"""Layer-config filtering collaborators for ColumnOrderService."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from bioetl.application.composite.column_orderer_group_flow import (
    apply_renames,
    filter_columns_by_explicit,
    filter_columns_by_groups,
)

if TYPE_CHECKING:
    from bioetl.domain.composite import ColumnGroupConfig, LayerColumnConfig
    from bioetl.domain.ports import LoggerPort

__all__ = ["filter_columns_by_layer_config"]


def filter_columns_by_layer_config(
    *,
    columns: Sequence[str],
    layer_config: LayerColumnConfig,
    column_groups: Sequence[ColumnGroupConfig] | None,
    collect_group_columns: Callable[[set[str], ColumnGroupConfig], list[str]],
    logger: LoggerPort,
) -> list[str]:
    """Filter columns by layer config and apply renames."""
    if layer_config.columns:
        filtered = filter_columns_by_explicit(
            columns=columns,
            layer_config=layer_config,
        )
    elif layer_config.include_groups:
        filtered = filter_columns_by_groups(
            columns=columns,
            layer_config=layer_config,
            column_groups=column_groups,
            collect_group_columns=collect_group_columns,
            logger=logger,
        )
    else:
        filtered = list(columns)

    if layer_config.rename_fields:
        filtered = apply_renames(filtered, layer_config.rename_fields)

    return filtered
