"""Domain service for business key computation.

This module provides pure domain logic for computing business keys
from entities. Business keys are used for deduplication and
identifying unique records regardless of storage location.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, Sequence

if TYPE_CHECKING:
    from bioetl.domain.entities.base import EntityBase


class BusinessKeyService:
    """Domain service for business key operations.

    This service encapsulates the domain logic for computing and
    comparing business keys from entities or raw records.

    The business key is a tuple of values from specific fields that
    uniquely identify a domain entity in a business context (as opposed
    to a technical primary key).

    Example:
        >>> service = BusinessKeyService()
        >>> key = service.compute_key_from_record(
        ...     record={
        ...         'molecule_chembl_id': 'CHEMBL25',
        ...         'assay_chembl_id': 'CHEMBL1000'
        ...     },
        ...     key_fields=['molecule_chembl_id', 'assay_chembl_id']
        ... )
        >>> print(key)
        ('CHEMBL25', 'CHEMBL1000')
    """

    def compute_key_from_entity(self, entity: "EntityBase") -> tuple[Any, ...]:
        """Compute business key from a domain entity.

        Uses the entity's BUSINESS_KEY_FIELDS class attribute to
        determine which fields comprise the business key.

        Args:
            entity: Domain entity instance.

        Returns:
            Tuple of values from business key fields.
        """
        return entity.get_business_key_values()

    def compute_key_from_record(
        self,
        record: Mapping[str, Any],
        key_fields: Sequence[str],
    ) -> tuple[Any, ...]:
        """Compute business key from a raw record dictionary.

        Args:
            record: Dictionary containing field values.
            key_fields: Sequence of field names comprising the business key.

        Returns:
            Tuple of values from business key fields.

        Raises:
            KeyError: If a required key field is missing from record.
        """
        return tuple(record[field] for field in key_fields)

    def compute_key_from_record_safe(
        self,
        record: Mapping[str, Any],
        key_fields: Sequence[str],
        default: Any = None,
    ) -> tuple[Any, ...]:
        """Compute business key with default for missing fields.

        Args:
            record: Dictionary containing field values.
            key_fields: Sequence of field names comprising the business key.
            default: Default value for missing fields.

        Returns:
            Tuple of values from business key fields (or defaults).
        """
        return tuple(record.get(field, default) for field in key_fields)

    def keys_match(
        self,
        key1: tuple[Any, ...],
        key2: tuple[Any, ...],
    ) -> bool:
        """Check if two business keys are equal.

        Args:
            key1: First business key tuple.
            key2: Second business key tuple.

        Returns:
            True if keys match, False otherwise.
        """
        return key1 == key2

    def serialize_key(self, key: tuple[Any, ...]) -> str:
        """Serialize business key to string for hashing.

        Converts each value to string and joins with a delimiter.
        Used as input to hash functions.

        Args:
            key: Business key tuple.

        Returns:
            String representation suitable for hashing.
        """
        return "|".join(str(v) if v is not None else "" for v in key)


# Module-level singleton for convenience
_business_key_service: BusinessKeyService | None = None


def get_business_key_service() -> BusinessKeyService:
    """Get singleton instance of BusinessKeyService.

    Returns:
        Shared BusinessKeyService instance.
    """
    global _business_key_service  # noqa: PLW0603
    if _business_key_service is None:
        _business_key_service = BusinessKeyService()
    return _business_key_service


__all__ = [
    "BusinessKeyService",
    "get_business_key_service",
]
