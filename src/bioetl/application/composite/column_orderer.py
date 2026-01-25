"""Column orderer service for composite pipelines.

Orders columns by semantic groups for consistent output.
See ADR-026 for rationale.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from bioetl.domain.value_objects.column_order import (
    DEFAULT_COLUMN_ORDER,
    ColumnOrderConfig,
    SemanticGroup,
)
from bioetl.domain.value_objects.column_qualifier import ColumnQualifier

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.ports import LoggerPort

__all__ = ["ColumnOrderer"]


class ColumnOrderer:
    """Service for ordering columns by semantic groups.

    Orders DataFrame columns in a consistent, semantically meaningful way:
    1. System fields (entity_id, _run_id, ...)
    2. Identifiers (doi, pmid, ...)
    3. Title fields
    4. Abstract fields
    5. Authors fields
    6. Journal/Source fields
    7. Date fields
    8. Metrics fields
    9. Classification fields
    10. URL fields
    11. Other fields

    Within each group, columns are ordered by:
    - Provider priority (chembl first, then crossref, etc.)
    - Alphabetically for same provider

    Example:
        >>> orderer = ColumnOrderer(logger)
        >>> result = orderer.order_columns(df)
        >>> result.columns[:5]
        ['entity_id', '_run_id', 'doi', 'pmid', 'chembl.publication.title']
    """

    def __init__(
        self,
        logger: LoggerPort,
        config: ColumnOrderConfig | None = None,
    ) -> None:
        """Initialize orderer.

        Args:
            logger: Logger port for diagnostics.
            config: Column order configuration. Uses DEFAULT_COLUMN_ORDER if None.
        """
        self._logger = logger
        self._config = config or DEFAULT_COLUMN_ORDER

    def order_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Order DataFrame columns by semantic groups.

        Args:
            df: DataFrame to reorder.

        Returns:
            DataFrame with columns in semantic order.
        """
        if not df.columns:
            return df

        ordered = self.get_ordered_columns(df.columns)

        self._logger.debug(
            "Ordered columns by semantic groups",
            total_columns=len(ordered),
            groups_used=self._count_groups(ordered),
        )

        return df.select(ordered)

    def get_ordered_columns(self, columns: Sequence[str]) -> list[str]:
        """Get columns in semantic order.

        Args:
            columns: Column names to order.

        Returns:
            Ordered list of column names.
        """
        # Create sort key for each column
        def sort_key(col: str) -> tuple[int, int, str]:
            """Sort by (group, provider_rank, column_name)."""
            group = self._config.get_group(col)
            provider_rank = self._config.get_provider_rank(col)
            # For alphabetical sort, use field name (not full qualified name)
            field_name = ColumnQualifier.extract_field(col)
            return (group.value, provider_rank, field_name.lower())

        return sorted(columns, key=sort_key)

    def _count_groups(self, columns: Sequence[str]) -> dict[str, int]:
        """Count columns per semantic group.

        Args:
            columns: Ordered column names.

        Returns:
            Dict mapping group name to column count.
        """
        counts: dict[str, int] = {}
        for col in columns:
            group = self._config.get_group(col)
            group_name = group.name
            counts[group_name] = counts.get(group_name, 0) + 1
        return counts

    def group_columns(
        self, columns: Sequence[str]
    ) -> dict[SemanticGroup, list[str]]:
        """Group columns by semantic type.

        Useful for debugging and documentation.

        Args:
            columns: Column names to group.

        Returns:
            Dict mapping SemanticGroup to list of columns.
        """
        groups: dict[SemanticGroup, list[str]] = {}

        for col in columns:
            group = self._config.get_group(col)
            if group not in groups:
                groups[group] = []
            groups[group].append(col)

        # Sort columns within each group
        for group in groups:
            groups[group] = sorted(
                groups[group],
                key=lambda c: (
                    self._config.get_provider_rank(c),
                    ColumnQualifier.extract_field(c).lower(),
                ),
            )

        return groups
