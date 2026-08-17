"""Column qualifier value object for unified naming.

Implements {provider}.{entity}.{field} naming convention.
See ADR-026 for rationale.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

__all__ = ["JOIN_KEY_COLUMNS", "ColumnQualifier"]

# Join keys excluded from renaming (case-insensitive)
JOIN_KEY_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "doi",
        "pmid",
        "pmc_id",
        "publication_id",
        "publication_doi",
        "publication_pmid",
        "publication_pmc_id",
    }
)


@dataclass(frozen=True, slots=True)
class ColumnQualifier:
    """Qualified column name in format {provider}.{entity}.{field}.

    Immutable value object representing a fully qualified column name.
    Used for consistent naming across composite pipelines.

    Attributes:
        provider: Data provider name (e.g., 'chembl', 'crossref').
        entity: Entity type (e.g., 'publication', 'activity').
        field: Field name (e.g., 'title', 'abstract').

    Example:
        >>> q = ColumnQualifier("chembl", "publication", "title")
        >>> str(q)
        'chembl.publication.title'
        >>> q.is_join_key
        False
    """

    provider: str
    entity: str
    field: str

    def __post_init__(self) -> None:
        """Validate and normalize fields."""
        for attr in ("provider", "entity", "field"):
            value = getattr(self, attr)
            normalized = self._validate_field(value, attr)
            object.__setattr__(self, attr, normalized)

    @staticmethod
    def _validate_field(value: str, name: str) -> str:
        """Validate non-empty and normalize to lowercase."""
        if not value or not value.strip():
            raise ValueError(f"{name} cannot be empty")
        return value.strip().lower()

    def __str__(self) -> str:
        """Return qualified name: {provider}.{entity}.{field}."""
        return f"{self.provider}.{self.entity}.{self.field}"

    @property
    def prefix(self) -> str:
        """Return prefix without field: {provider}.{entity}."""
        return f"{self.provider}.{self.entity}"

    @property
    def is_join_key(self) -> bool:
        """Check if field is a join key (publication identifiers)."""
        return self.field.lower() in JOIN_KEY_COLUMNS

    @classmethod
    def from_pipeline(cls, pipeline: str, field: str) -> ColumnQualifier:
        """Create from pipeline name and field.

        Args:
            pipeline: Pipeline name in format 'provider_entity'.
            field: Column field name.

        Returns:
            ColumnQualifier instance.

        Raises:
            ValueError: If pipeline format is invalid.

        Example:
            >>> q = ColumnQualifier.from_pipeline("chembl_publication", "title")
            >>> str(q)
            'chembl.publication.title'
        """
        if "_" not in pipeline:
            raise ValueError(
                f"Pipeline '{pipeline}' must be in format 'provider_entity'"
            )
        provider, entity = pipeline.split("_", 1)
        return cls(provider=provider, entity=entity, field=field)

    @classmethod
    def parse(cls, qualified_name: str) -> ColumnQualifier:
        """Parse qualified name back to ColumnQualifier.

        Args:
            qualified_name: Qualified name in format 'provider.entity.field'.

        Returns:
            ColumnQualifier instance.

        Raises:
            ValueError: If format is invalid.

        Example:
            >>> q = ColumnQualifier.parse("chembl.publication.title")
            >>> q.provider
            'chembl'
        """
        # Split from the left with maxsplit=2 so field may contain dots.
        parts = qualified_name.split(".", 2)
        if len(parts) != 3 or not all(p.strip() for p in parts):
            raise ValueError(
                f"Qualified name '{qualified_name}' must have format "
                "provider.entity.field (field may contain additional dots)"
            )
        return cls(provider=parts[0], entity=parts[1], field=parts[2])

    @staticmethod
    def is_qualified(column: str) -> bool:
        """Check if column name is already in qualified format.

        Args:
            column: Column name to check.

        Returns:
            True if column has format x.y.z (3 dot-separated parts).
        """
        parts = column.split(".", 2)
        return len(parts) == 3 and all(p.strip() for p in parts)

    @staticmethod
    def extract_field(column: str) -> str:
        """Extract field name from column (qualified or unqualified).

        For qualified names (provider.entity.field), returns the field part.
        For unqualified names, returns the original column name.

        Args:
            column: Column name (qualified or unqualified).

        Returns:
            Field name.

        Example:
            >>> ColumnQualifier.extract_field("chembl.publication.title")
            'title'
            >>> ColumnQualifier.extract_field("title")
            'title'
        """
        parts = column.split(".", 2)
        if len(parts) == 3:
            return parts[2]
        return column
