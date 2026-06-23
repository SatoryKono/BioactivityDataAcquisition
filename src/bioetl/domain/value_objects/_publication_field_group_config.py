"""Field-group configuration helpers for publication columns."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from bioetl.domain.value_objects.publication_field_group_types import (
    FIELD_TO_GROUP_MAPPING,
    PublicationFieldGroup,
)

__all__ = [
    "DEFAULT_FIELD_GROUP_CONFIG",
    "FieldGroupConfig",
]


@dataclass(frozen=True, slots=True)
class FieldGroupConfig:
    """Configuration for publication-field grouping operations."""

    field_groups: dict[str, PublicationFieldGroup] = field(
        default_factory=lambda: dict(FIELD_TO_GROUP_MAPPING)
    )
    provider_priority: tuple[str, ...] = (
        "chembl",
        "crossref",
        "openalex",
        "pubmed",
        "semanticscholar",
    )
    default_group: PublicationFieldGroup = PublicationFieldGroup.TRASH

    def get_group(self, column: str) -> PublicationFieldGroup:
        """Get semantic group for qualified or unqualified column name.

        Args:
            column: Column name (qualified as 'provider.entity.field' or unqualified).

        Returns:
            PublicationFieldGroup for the column, or default group if unmapped.
        """
        field_name = self._extract_field(column)
        return self.field_groups.get(field_name, self.default_group)

    def is_gold_field(self, column: str) -> bool:
        """Check if a column should be included in Gold layer.

        Args:
            column: Column name to check.

        Returns:
            True if the column belongs to a Gold-included group, False otherwise.
        """
        return self.get_group(column).include_in_gold

    def get_gold_columns(self, columns: list[str]) -> list[str]:
        """Filter columns to Gold-included fields.

        Args:
            columns: List of column names to filter.

        Returns:
            List of column names that belong to Gold-included groups.
        """
        return [column for column in columns if self.is_gold_field(column)]

    def get_trash_columns(self, columns: list[str]) -> list[str]:
        """Return columns excluded from Gold layer.

        Args:
            columns: List of column names to filter.

        Returns:
            List of column names that are excluded from Gold-included groups.
        """
        return [column for column in columns if not self.is_gold_field(column)]

    def get_columns_by_group(
        self, columns: list[str], group: PublicationFieldGroup
    ) -> list[str]:
        """Return columns that belong to the given group.

        Args:
            columns: List of column names to filter.
            group: Semantic group to filter by.

        Returns:
            List of column names belonging to the specified semantic group.
        """
        return [column for column in columns if self.get_group(column) == group]

    def group_columns(
        self, columns: list[str]
    ) -> dict[PublicationFieldGroup, list[str]]:
        """Group columns by semantic groups.

        Args:
            columns: List of column names to group.

        Returns:
            Dictionary mapping each PublicationFieldGroup to its list of columns.
        """
        result: dict[PublicationFieldGroup, list[str]] = {
            group: [] for group in PublicationFieldGroup
        }
        for column in columns:
            result[self.get_group(column)].append(column)
        return result

    def get_provider_rank(self, column: str) -> int:
        """Return provider rank for ordering within semantic group.

        Args:
            column: Column name (qualified as 'provider.entity.field' or unqualified).

        Returns:
            Integer provider rank (-1 for unqualified columns, 999 for unknown providers).
        """
        parts = column.split(".")
        if len(parts) != 3:
            return -1
        provider = parts[0].lower()
        try:
            return self.provider_priority.index(provider)
        except ValueError:
            return 999

    def sort_columns(self, columns: list[str]) -> list[str]:
        """Sort by semantic group, provider priority, then field name.

        Args:
            columns: List of column names to sort.

        Returns:
            Sorted list of column names by group, provider priority, and field name.
        """

        def sort_key(column: str) -> tuple[int, int, str]:
            group = self.get_group(column)
            provider_rank = self.get_provider_rank(column)
            field_name = self._extract_field(column)
            return (list(PublicationFieldGroup).index(group), provider_rank, field_name)

        return sorted(columns, key=sort_key)

    def _extract_field(self, column: str) -> str:
        """Extract field name from qualified or unqualified column."""
        parts = column.split(".")
        if len(parts) == 3:
            return parts[2].lower()
        return column.lower()

    def get_field_providers(self, field_name: str) -> list[str]:
        """Return providers expected to supply the given field.

        Args:
            field_name: Field name to look up (case-insensitive).

        Returns:
            List of provider names expected to supply the field, or empty list if unmapped.
        """
        normalized = field_name.lower()
        if normalized in self.field_groups:
            return list(self.provider_priority)
        return []


DEFAULT_FIELD_GROUP_CONFIG: Final[FieldGroupConfig] = FieldGroupConfig()
