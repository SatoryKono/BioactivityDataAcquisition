"""Column Qualifier Value Object.

Represents a fully qualified column name in the format {provider}.{entity}.{field}.
Used for unified column naming in composite pipelines.

See ADR-026.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class ColumnQualifier:
    """Qualified column name value object.

    Encapsulates the naming convention {provider}.{entity}.{field}
    ensuring all components are valid, lowercase, and properly formatted.
    """

    provider: str
    entity: str
    field: str

    _JOIN_KEY_FIELDS: frozenset[str] = frozenset({"doi", "pmid", "pmc_id"})

    def __post_init__(self) -> None:
        """Validate and normalize fields."""
        if not self.provider:
            raise ValueError("Provider cannot be empty")
        if not self.entity:
            raise ValueError("Entity cannot be empty")
        if not self.field:
            raise ValueError("Field cannot be empty")

        # Normalize to lowercase if not already
        if not self.provider.islower():
            object.__setattr__(self, "provider", self.provider.lower())
        if not self.entity.islower():
            object.__setattr__(self, "entity", self.entity.lower())
        if not self.field.islower():
            object.__setattr__(self, "field", self.field.lower())

    def __str__(self) -> str:
        """Return the qualified string representation."""
        return f"{self.provider}.{self.entity}.{self.field}"

    @classmethod
    def from_pipeline(cls, pipeline: str, field: str) -> Self:
        """Create from pipeline name and field.

        Args:
            pipeline: Pipeline name in format "provider_entity" (e.g., "chembl_publication").
            field: Field name (e.g., "title").

        Returns:
            ColumnQualifier instance.

        Raises:
            ValueError: If pipeline name is invalid format.
        """
        if "_" not in pipeline:
            raise ValueError(
                f"Invalid pipeline name format: '{pipeline}'. Expected 'provider_entity'."
            )

        provider, entity = pipeline.split("_", 1)
        return cls(provider=provider, entity=entity, field=field)

    @classmethod
    def parse(cls, qualified_name: str) -> Self:
        """Parse a qualified name string.

        Args:
            qualified_name: String in format "provider.entity.field".

        Returns:
            ColumnQualifier instance.

        Raises:
            ValueError: If string format is invalid.
        """
        parts = qualified_name.split(".")
        if len(parts) != 3:
            raise ValueError(
                f"Invalid qualified name format: '{qualified_name}'. "
                "Expected 'provider.entity.field'."
            )

        return cls(provider=parts[0], entity=parts[1], field=parts[2])

    @property
    def is_join_key(self) -> bool:
        """Check if the field is a join key (doi, pmid, pmc_id)."""
        return self.field in self._JOIN_KEY_FIELDS
