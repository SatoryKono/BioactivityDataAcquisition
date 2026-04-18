"""Deprecated compatibility facade for semantic column ordering."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from bioetl.application.composite.column_service import (
    ColumnOrderService,
    collect_explicit_group_columns,
    collect_pattern_columns,
    extract_field_from_qualified_name,
    resolve_publication_field_aliases,
    sort_columns_by_provider,
)
from bioetl.domain.value_objects.column_order import ColumnOrderConfig

if TYPE_CHECKING:
    from bioetl.domain.composite.config import ColumnGroupConfig
    from bioetl.domain.ports import LoggerPort

__all__ = ["ColumnOrderer"]


class ColumnOrderer(ColumnOrderService):
    """Backward-compatible alias for :class:`ColumnOrderService`.

    .. deprecated:: 2024.2
        Use :class:`ColumnOrderService` instead for unified column ordering
        functionality.
    """

    def __init__(
        self,
        logger: LoggerPort,
        config: ColumnOrderConfig | None = None,
        column_groups: Sequence[ColumnGroupConfig] | None = None,
    ) -> None:
        """Initialize deprecated semantic column ordering facade."""
        import warnings

        warnings.warn(
            "ColumnOrderer is deprecated and will be removed in a future version. "
            "Use ColumnOrderService instead for unified column ordering "
            "functionality.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(logger, config=config, column_groups=column_groups)
