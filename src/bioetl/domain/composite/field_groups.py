"""Field group domain models for Composite Publication Pipeline.

Provides semantic grouping of publication fields across providers for:
- Column ordering in merged output (groups appear in enum order)
- Gold layer filtering (excluding trash group)
- Provider-to-field mapping with qualified column tracking

Domain models:
- FieldMapping: Maps base field name to provider-qualified columns
- FieldGroupDefinition: Defines a semantic group with its fields
- FieldGroupRegistry: Central registry for field group operations

See ADR-026 for Composite Publication Pipeline rationale.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from bioetl.domain.value_objects.publication_field_groups import (
    PublicationFieldGroup,
)

# Re-export for convenience (canonical type used throughout)
FieldGroupId = PublicationFieldGroup

__all__ = [
    "DEFAULT_PROVIDER_ORDER",
    "FieldGroupDefinition",
    "FieldGroupId",
    "FieldGroupRegistry",
    "FieldMapping",
    "build_field_group_registry",
]

DEFAULT_PROVIDER_ORDER: Final[tuple[str, ...]] = (
    "chembl",
    "crossref",
    "openalex",
    "pubmed",
    "semanticscholar",
)


@dataclass(frozen=True, slots=True)
class FieldMapping:
    """Maps a base field name to its provider-qualified columns and group.

    Each field can appear in multiple providers with qualified column names
    following the ``{provider}.{entity}.{field}`` convention.

    Attributes:
        base_name: Base field name (e.g., "title", "doi").
        provider_columns: Qualified column names from each provider
            (e.g., ("chembl.publication.title", "crossref.publication.title")).
        group: Semantic group this field belongs to.

    Example:
        >>> mapping = FieldMapping(
        ...     base_name="title",
        ...     provider_columns=("chembl.publication.title", "crossref.publication.title"),
        ...     group=FieldGroupId.BIBLIOGRAPHY,
        ... )
        >>> mapping.providers
        ('chembl', 'crossref')
        >>> mapping.has_provider("crossref")
        True
    """

    base_name: str
    provider_columns: tuple[str, ...] = ()
    group: FieldGroupId = FieldGroupId.TRASH

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if isinstance(self.provider_columns, list):
            object.__setattr__(self, "provider_columns", tuple(self.provider_columns))
        if not self.base_name:
            raise ValueError("base_name cannot be empty")

    @property
    def providers(self) -> tuple[str, ...]:
        """Extract provider names from qualified columns."""
        result: list[str] = []
        for col in self.provider_columns:
            parts = col.split(".")
            if len(parts) == 3 and parts[0] not in result:
                result.append(parts[0])
        return tuple(result)

    @property
    def provider_count(self) -> int:
        """Number of providers that have this field."""
        return len(self.providers)

    def has_provider(self, provider: str) -> bool:
        """Check if a specific provider has this field.

        Args:
            provider: Data provider name.

        Returns:
            True if the condition is met, False otherwise.
        """
        return provider.lower() in (p.lower() for p in self.providers)

    def get_column(self, provider: str) -> str | None:
        """Get qualified column name for a specific provider.

        Args:
            provider: Data provider name.

        Returns:
            Column.
        """
        provider_lower = provider.lower()
        for col in self.provider_columns:
            parts = col.split(".")
            if len(parts) == 3 and parts[0].lower() == provider_lower:
                return col
        return None


@dataclass(frozen=True, slots=True)
class FieldGroupDefinition:
    """Defines a semantic group with its fields.

    Attributes:
        group_id: The semantic group identifier.
        display_name: Human-readable name for the group.
        include_in_gold: Whether fields in this group are included in Gold layer.
        fields: Tuple of FieldMapping objects belonging to this group.

    Example:
        >>> group = FieldGroupDefinition(
        ...     group_id=FieldGroupId.BIBLIOGRAPHY,
        ...     display_name="Bibliography",
        ...     include_in_gold=True,
        ...     fields=(
        ...         FieldMapping("title", ("chembl.publication.title",), FieldGroupId.BIBLIOGRAPHY),
        ...     ),
        ... )
        >>> group.base_field_names
        ('title',)
    """

    group_id: FieldGroupId
    display_name: str
    include_in_gold: bool = True
    fields: tuple[FieldMapping, ...] = ()

    def __post_init__(self) -> None:
        """Convert types."""
        if isinstance(self.fields, list):
            object.__setattr__(self, "fields", tuple(self.fields))

    @property
    def base_field_names(self) -> tuple[str, ...]:
        """Get all base field names in this group."""
        return tuple(f.base_name for f in self.fields)

    @property
    def all_columns(self) -> tuple[str, ...]:
        """Get all provider-qualified columns across all fields in this group."""
        result: list[str] = []
        for f in self.fields:
            result.extend(f.provider_columns)
        return tuple(result)

    @property
    def field_count(self) -> int:
        """Number of fields in this group."""
        return len(self.fields)


class FieldGroupRegistry:
    """Central registry for field group operations.

    Provides efficient lookup, filtering, and ordering of publication
    fields based on semantic groups and provider sources.

    This registry is built from YAML configuration and injected into
    services that need field group awareness (MergeService, GoldWriter).

    Example:
        >>> registry = FieldGroupRegistry(groups=(...), provider_order=(...))
        >>> registry.get_group("title")
        <PublicationFieldGroup.BIBLIOGRAPHY: 'bibliography'>
        >>> gold_cols = registry.get_gold_columns(["chembl.publication.title", "content_hash"])
        >>> gold_cols
        ['chembl.publication.title']
    """

    def __init__(
        self,
        groups: tuple[FieldGroupDefinition, ...],
        provider_order: tuple[str, ...] = DEFAULT_PROVIDER_ORDER,
        default_group: FieldGroupId = FieldGroupId.TRASH,
    ) -> None:
        """Build the registry and pre-compute lookup indices for fast field resolution.

        Iterates over ``groups`` once at construction time to build four internal
        dictionaries: field-name to group, qualified-column to group, field-name to
        ``FieldMapping``, and group-id to ``FieldGroupDefinition``. All public
        methods then operate in O(1) average time. See ADR-026 for the composite
        pipeline design that relies on this registry.

        Args:
            groups: Tuple of ``FieldGroupDefinition`` objects defining all semantic
                field groups and their provider-qualified columns.
            provider_order: Provider priority order used when sorting columns within
                the same semantic group; defaults to ``DEFAULT_PROVIDER_ORDER``.
            default_group: ``FieldGroupId`` assigned to any column not found in the
                registry; defaults to ``FieldGroupId.TRASH`` (excluded from Gold layer).
        """
        self._groups = groups
        self._provider_order = provider_order
        self._default_group = default_group

        # Build indices for fast lookup
        self._field_to_group: dict[str, FieldGroupId] = {}
        self._column_to_group: dict[str, FieldGroupId] = {}
        self._field_to_mapping: dict[str, FieldMapping] = {}
        self._group_to_def: dict[FieldGroupId, FieldGroupDefinition] = {}

        for group_def in groups:
            self._group_to_def[group_def.group_id] = group_def
            for fm in group_def.fields:
                self._field_to_group[fm.base_name.lower()] = fm.group
                self._field_to_mapping[fm.base_name.lower()] = fm
                for col in fm.provider_columns:
                    self._column_to_group[col.lower()] = fm.group

    @property
    def groups(self) -> tuple[FieldGroupDefinition, ...]:
        """All group definitions."""
        return self._groups

    @property
    def provider_order(self) -> tuple[str, ...]:
        """Provider priority order."""
        return self._provider_order

    @property
    def field_count(self) -> int:
        """Total number of mapped base fields."""
        return len(self._field_to_group)

    @property
    def column_count(self) -> int:
        """Total number of mapped provider columns."""
        return len(self._column_to_group)

    def get_group(self, column: str) -> FieldGroupId:
        """Get semantic group for a column or field name.

        Handles both qualified (provider.entity.field) and
        unqualified (field) column names.

        Args:
            column: Column name (qualified or unqualified).

        Returns:
            FieldGroupId for the column.
        """
        # Try exact match on qualified column
        col_lower = column.lower()
        if col_lower in self._column_to_group:
            return self._column_to_group[col_lower]

        # Try base field name extraction
        field_name = self._extract_field(column)
        return self._field_to_group.get(field_name, self._default_group)

    def get_field_mapping(self, base_name: str) -> FieldMapping | None:
        """Get FieldMapping for a base field name.

        Args:
            base_name: Name of the base.

        Returns:
            Field mapping.
        """
        return self._field_to_mapping.get(base_name.lower())

    def get_group_definition(
        self, group_id: FieldGroupId
    ) -> FieldGroupDefinition | None:
        """Get FieldGroupDefinition for a group ID.

        Args:
            group_id: Identifier for group.

        Returns:
            Group definition.
        """
        return self._group_to_def.get(group_id)

    def is_gold_field(self, column: str) -> bool:
        """Check if a column should be included in Gold layer.

        Args:
            column: Column name.

        Returns:
            True if the condition is met, False otherwise.
        """
        return self.get_group(column).include_in_gold

    def get_gold_columns(self, columns: list[str]) -> list[str]:
        """Filter columns to only those included in Gold layer.

        System columns (starting with ``_``) are always included.

        Args:
            columns: List of column names.

        Returns:
            Filtered list of Gold-layer columns.
        """
        return [c for c in columns if c.startswith("_") or self.is_gold_field(c)]

    def get_trash_columns(self, columns: list[str]) -> list[str]:
        """Get columns that would be excluded from Gold layer.

        Args:
            columns: List of column names.

        Returns:
            List of trash columns (excluding system columns).
        """
        return [
            c for c in columns if not c.startswith("_") and not self.is_gold_field(c)
        ]

    def get_columns_by_group(
        self, columns: list[str], group: FieldGroupId
    ) -> list[str]:
        """Get columns belonging to a specific group.

        Args:
            columns: List of column names.
            group: Group.

        Returns:
            Columns by group.
        """
        return [c for c in columns if self.get_group(c) == group]

    def get_ordered_columns(self, columns: list[str]) -> list[str]:
        """Sort columns by semantic group and provider priority.

        Ordering:
        1. Semantic group (enum order)
        2. Provider priority (per provider_order)
        3. Field name (alphabetical)

        System columns (``_*``) are appended at the end.

        Args:
            columns: List of column names to sort.

        Returns:
            Sorted list of columns.
        """
        system_cols = [c for c in columns if c.startswith("_")]
        data_cols = [c for c in columns if not c.startswith("_")]

        group_order = list(FieldGroupId)

        def sort_key(column: str) -> tuple[int, int, str]:
            """Return (group_index, provider_rank, field) for ordering.

            Args:
                column: Column name.

            Returns:
                Sort key value for ordering.
            """
            group = self.get_group(column)
            try:
                group_idx = group_order.index(group)
            except ValueError:
                group_idx = len(group_order)

            provider_rank = self._get_provider_rank(column)
            field_name = self._extract_field(column)
            return (group_idx, provider_rank, field_name)

        sorted_data = sorted(data_cols, key=sort_key)
        return sorted_data + sorted(system_cols)

    def validate_columns(self, columns: list[str]) -> dict[str, list[str]]:
        """Validate columns against the registry.

        Returns:
            Dict with keys 'mapped', 'unmapped', 'system' listing columns.

        Args:
            columns: List of column names.
        """
        mapped: list[str] = []
        unmapped: list[str] = []
        system: list[str] = []

        for col in columns:
            if col.startswith("_"):
                system.append(col)
            elif self.get_group(col) != self._default_group:
                mapped.append(col)
            else:
                # Check if the extracted field name is mapped
                field_name = self._extract_field(col)
                if field_name in self._field_to_group:
                    mapped.append(col)
                else:
                    unmapped.append(col)

        return {"mapped": mapped, "unmapped": unmapped, "system": system}

    def _get_provider_rank(self, column: str) -> int:
        """Get provider rank for ordering within semantic group."""
        parts = column.split(".")
        if len(parts) == 3:
            provider = parts[0].lower()
            try:
                return self._provider_order.index(provider)
            except ValueError:
                return 999
        # Unqualified columns come first (seed)
        return -1

    @staticmethod
    def _extract_field(column: str) -> str:
        """Extract base field name from column (qualified or unqualified)."""
        parts = column.split(".")
        if len(parts) == 3:
            return parts[2].lower()
        return column.lower()


def build_field_group_registry(
    groups: tuple[FieldGroupDefinition, ...],
    provider_order: tuple[str, ...] = DEFAULT_PROVIDER_ORDER,
    default_group: FieldGroupId = FieldGroupId.TRASH,
) -> FieldGroupRegistry:
    """Factory function to create a FieldGroupRegistry.

    Args:
        groups: Tuple of FieldGroupDefinition objects.
        provider_order: Provider priority order for column sorting.
        default_group: Default group for unmapped fields.

    Returns:
        Configured FieldGroupRegistry instance.
    """
    return FieldGroupRegistry(
        groups=groups,
        provider_order=provider_order,
        default_group=default_group,
    )
