"""Field-group domain models for composite publication pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from bioetl.domain.value_objects.publication_field_group_types import (
    PublicationFieldGroup,
)

FieldGroupId = PublicationFieldGroup

__all__ = [
    "DEFAULT_PROVIDER_ORDER",
    "FieldGroupDefinition",
    "FieldGroupId",
    "FieldMapping",
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
    """Map a base field name to provider-qualified columns and semantic group."""

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
        """Extract provider names from qualified columns (case-insensitive)."""
        result: list[str] = []
        seen: set[str] = set()
        for col in self.provider_columns:
            parts = col.split(".")
            if len(parts) != 3:
                continue
            provider = parts[0].lower()
            if provider not in seen:
                seen.add(provider)
                result.append(provider)
        return tuple(result)

    @property
    def provider_count(self) -> int:
        """Number of providers that have this field."""
        return len(self.providers)

    def has_provider(self, provider: str) -> bool:
        """Check if a specific provider has this field.

        Args:
            provider: Provider name to check (case-insensitive).

        Returns:
            True if this field is available from the specified provider.
        """
        return provider.lower() in self.providers

    def get_column(self, provider: str) -> str | None:
        """Get qualified column name for a specific provider.

        Args:
            provider: Provider name to look up (case-insensitive).

        Returns:
            Qualified column name (e.g. 'chembl.publication.doi'), or None if provider has no mapping.
        """
        provider_lower = provider.lower()
        for col in self.provider_columns:
            parts = col.split(".")
            if len(parts) == 3 and parts[0].lower() == provider_lower:
                return col
        return None


@dataclass(frozen=True, slots=True)
class FieldGroupDefinition:
    """Semantic field group with display metadata and mappings."""

    group_id: FieldGroupId
    display_name: str
    include_in_gold: bool = True
    fields: tuple[FieldMapping, ...] = ()

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if not self.display_name:
            raise ValueError("display_name cannot be empty")
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
