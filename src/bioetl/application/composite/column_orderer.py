"""Column orderer service for composite pipelines.

Orders columns by semantic groups for consistent output.
See ADR-026 for rationale.
"""

from __future__ import annotations

import re
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

    from bioetl.domain.composite.config import ColumnGroupConfig
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
        column_groups: Sequence[ColumnGroupConfig] | None = None,
    ) -> None:
        """Initialize orderer.

        Args:
            logger: Logger port for diagnostics.
            config: Column order configuration. Uses DEFAULT_COLUMN_ORDER if None.
            column_groups: Optional YAML-based column group configuration.
                If provided, takes precedence over config.
        """
        self._logger = logger
        self._config = config or DEFAULT_COLUMN_ORDER
        self._column_groups = tuple(column_groups) if column_groups else None

    def order_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Order DataFrame columns by semantic groups.

        If column_groups were provided in constructor, uses YAML-based ordering.
        Otherwise falls back to hardcoded ColumnOrderConfig.

        Args:
            df: DataFrame to reorder.

        Returns:
            DataFrame with columns in semantic order.
        """
        if not df.columns:
            return df

        # Use YAML-based column groups if available
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
        """Order column names by semantic groups.

        Uses YAML-based column groups when configured, otherwise falls back
        to the default semantic ordering.
        """
        if not columns:
            return []

        if self._column_groups:
            return self._order_by_yaml_groups(columns)

        return self.get_ordered_columns(columns)

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

    def group_columns(self, columns: Sequence[str]) -> dict[SemanticGroup, list[str]]:
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

    # === YAML-based column ordering methods ===

    def _order_by_yaml_groups(self, columns: Sequence[str]) -> list[str]:
        """Order columns using YAML-configured groups.

        Args:
            columns: Column names to order.

        Returns:
            Ordered list of column names.
        """
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

        # Add remaining columns at the end (alphabetically)
        remaining = sorted(all_columns - used_columns)
        if remaining:
            ordered_columns.extend(remaining)
            self._logger.debug(
                "Ungrouped columns added at end",
                count=len(remaining),
                sample=remaining[:5],
            )

        return ordered_columns

    def _collect_group_columns(
        self,
        available: set[str],
        group: ColumnGroupConfig,
    ) -> list[str]:
        """Collect columns for a group, ordered by provider.

        Args:
            available: Set of available column names.
            group: Column group configuration.

        Returns:
            Ordered list of columns for this group.
        """
        matched: set[str] = set()

        # Match by explicit field names
        for field in group.fields:
            for col in available:
                # Match exact field name or suffixed versions
                field_name = self._extract_field_from_qualified(col)
                if field_name == field or col == field:
                    matched.add(col)

        # Match by pattern
        if group.pattern:
            try:
                pattern = re.compile(group.pattern, re.IGNORECASE)
                for col in available:
                    if pattern.search(col):
                        matched.add(col)
            except re.error as e:
                self._logger.warning(
                    "Invalid regex pattern in column group",
                    group=group.name,
                    pattern=group.pattern,
                    error=str(e),
                )

        # Sort by provider order
        return self._sort_by_provider(list(matched), group.provider_order)

    def _sort_by_provider(
        self,
        columns: list[str],
        provider_order: tuple[str, ...],
    ) -> list[str]:
        """Sort columns by provider prefix order.

        Seed columns (no dots) come first, then by provider order.

        Args:
            columns: List of column names.
            provider_order: Tuple of provider names in desired order.

        Returns:
            Sorted list of columns.
        """

        def sort_key(col: str) -> tuple[int, str]:
            # Seed columns (no dot or single dot like 'field.A') come first
            parts = col.split(".")
            if len(parts) < 3:
                return (0, col.lower())

            # Extract provider from qualified name (provider.entity.field)
            provider = parts[0].lower()
            try:
                idx = provider_order.index(provider)
                return (idx + 1, col.lower())
            except ValueError:
                # Unknown provider - at the end
                return (len(provider_order) + 1, col.lower())

        return sorted(columns, key=sort_key)

    def _extract_field_from_qualified(self, column: str) -> str:
        """Extract field name from qualified column name.

        Args:
            column: Column name (qualified or unqualified).

        Returns:
            Field name (last part of qualified name, or full name if unqualified).
        """
        parts = column.split(".")
        if len(parts) == 3:
            return parts[2]  # provider.entity.field -> field
        if len(parts) == 2:
            return parts[1]  # field.A -> A (conflict suffix) - keep original
        return column
