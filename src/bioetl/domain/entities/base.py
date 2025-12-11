"""Base classes for domain entities.

This module provides the foundation for domain entities following DDD principles.
Entities are objects with identity that persist over time and have business logic
encapsulated within them.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Mapping


@dataclass(frozen=True)
class EntityBase(ABC):
    """Abstract base class for domain entities.

    Entities are domain objects that have a distinct identity and lifecycle.
    They encapsulate business rules and invariants related to the concept
    they represent.

    Subclasses must define:
        - BUSINESS_KEY_FIELDS: Fields used to compute the business key hash
        - PRIMARY_KEY_FIELD: The primary identifier field name

    Features:
        - Immutable by default (frozen=True)
        - Business key computation for deduplication
        - Validation of invariants in __post_init__
    """

    # Class-level configuration (to be overridden by subclasses)
    BUSINESS_KEY_FIELDS: ClassVar[tuple[str, ...]] = ()
    PRIMARY_KEY_FIELD: ClassVar[str] = ""

    def get_business_key_values(self) -> tuple[Any, ...]:
        """Return values of business key fields as a tuple.

        Used for computing business key hash for deduplication.

        Returns:
            Tuple of values from business key fields.

        Example:
            >>> activity.get_business_key_values()
            ('CHEMBL123', 'CHEMBL456', 'IC50', 10.5, 'nM')
        """
        return tuple(getattr(self, f) for f in self.BUSINESS_KEY_FIELDS)

    def get_primary_key(self) -> Any:
        """Return the primary key value.

        Returns:
            The value of the primary key field.
        """
        return getattr(self, self.PRIMARY_KEY_FIELD)

    @classmethod
    def get_field_names(cls) -> tuple[str, ...]:
        """Return all field names defined on this entity.

        Returns:
            Tuple of field names.
        """
        # Get fields from dataclass
        if hasattr(cls, "__dataclass_fields__"):
            return tuple(cls.__dataclass_fields__.keys())
        return ()

    @classmethod
    @abstractmethod
    def from_record(cls, record: Mapping[str, Any]) -> "EntityBase":
        """Create an entity instance from a raw record dictionary.

        This factory method handles the conversion from raw API/database
        records to strongly-typed domain entities.

        Args:
            record: Dictionary containing field values.

        Returns:
            New entity instance.

        Raises:
            ValueError: If required fields are missing or invalid.
        """

    def to_record(self) -> dict[str, Any]:
        """Convert entity to a dictionary record.

        Returns:
            Dictionary with all entity fields.
        """
        return {f: getattr(self, f) for f in self.get_field_names()}


def extract_field(
    record: Mapping[str, Any],
    field_name: str,
    *,
    required: bool = False,
    default: Any = None,
    coerce: type | None = None,
) -> Any:
    """Extract a field from a record with optional coercion.

    Helper function for entity from_record() implementations.

    Args:
        record: Source dictionary.
        field_name: Key to extract.
        required: If True, raise ValueError when field is missing.
        default: Default value when field is missing (ignored if required=True).
        coerce: Optional type to coerce the value to.

    Returns:
        Extracted and optionally coerced value.

    Raises:
        ValueError: If required field is missing or coercion fails.
    """
    value = record.get(field_name, default)

    if required and value is None:
        raise ValueError(f"Required field '{field_name}' is missing")

    if value is not None and coerce is not None:
        try:
            value = coerce(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Cannot coerce field '{field_name}' to {coerce.__name__}: {exc}"
            ) from exc

    return value


__all__ = [
    "EntityBase",
    "extract_field",
]
