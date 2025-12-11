"""Domain factory for creating entities from raw records.

This module provides a factory service that creates the appropriate
entity type from raw record dictionaries based on entity name.
"""

from __future__ import annotations

from typing import Any, Mapping

from bioetl.domain.entities import (
    Activity,
    Assay,
    Cell,
    EntityBase,
    Molecule,
    Publication,
    Target,
    Tissue,
)


class EntityFactory:
    """Factory for creating domain entities from raw records.

    This factory provides a unified interface for creating entities
    based on entity type name, abstracting away the specific entity
    class details from calling code.

    Example:
        >>> factory = EntityFactory()
        >>> activity = factory.create('activity', raw_record)
        >>> target = factory.create('target', target_data)
    """

    # Mapping of entity names to entity classes
    _ENTITY_MAP: dict[str, type[EntityBase]] = {
        "activity": Activity,
        "assay": Assay,
        "cell": Cell,
        "molecule": Molecule,
        "publication": Publication,
        "document": Publication,  # Alias
        "target": Target,
        "tissue": Tissue,
    }

    def create(
        self,
        entity_name: str,
        record: Mapping[str, Any],
    ) -> EntityBase:
        """Create an entity instance from a raw record.

        Args:
            entity_name: Name of the entity type (e.g., 'activity', 'target').
            record: Raw record dictionary.

        Returns:
            Domain entity instance of the appropriate type.

        Raises:
            ValueError: If entity_name is not recognized.
        """
        entity_class = self._get_entity_class(entity_name)
        return entity_class.from_record(record)

    def create_many(
        self,
        entity_name: str,
        records: list[Mapping[str, Any]],
    ) -> list[EntityBase]:
        """Create multiple entity instances from raw records.

        Args:
            entity_name: Name of the entity type.
            records: List of raw record dictionaries.

        Returns:
            List of domain entity instances.

        Raises:
            ValueError: If entity_name is not recognized.
        """
        entity_class = self._get_entity_class(entity_name)
        return [entity_class.from_record(record) for record in records]

    def _get_entity_class(self, entity_name: str) -> type[EntityBase]:
        """Get entity class by name.

        Args:
            entity_name: Name of the entity type.

        Returns:
            Entity class.

        Raises:
            ValueError: If entity_name is not recognized.
        """
        normalized = entity_name.lower().strip()
        entity_class = self._ENTITY_MAP.get(normalized)
        if entity_class is None:
            valid_names = sorted(self._ENTITY_MAP.keys())
            raise ValueError(
                f"Unknown entity type: '{entity_name}'. "
                f"Valid types are: {', '.join(valid_names)}"
            )
        return entity_class

    def get_supported_entities(self) -> list[str]:
        """Return list of supported entity names.

        Returns:
            List of entity type names that can be created.
        """
        return sorted(set(self._ENTITY_MAP.keys()) - {"document"})

    def get_entity_class(self, entity_name: str) -> type[EntityBase]:
        """Get entity class by name (public accessor).

        Args:
            entity_name: Name of the entity type.

        Returns:
            Entity class.

        Raises:
            ValueError: If entity_name is not recognized.
        """
        return self._get_entity_class(entity_name)

    def get_business_key_fields(self, entity_name: str) -> tuple[str, ...]:
        """Get business key fields for an entity type.

        Args:
            entity_name: Name of the entity type.

        Returns:
            Tuple of field names that comprise the business key.

        Raises:
            ValueError: If entity_name is not recognized.
        """
        entity_class = self._get_entity_class(entity_name)
        return entity_class.BUSINESS_KEY_FIELDS

    def get_primary_key_field(self, entity_name: str) -> str:
        """Get primary key field name for an entity type.

        Args:
            entity_name: Name of the entity type.

        Returns:
            Name of the primary key field.

        Raises:
            ValueError: If entity_name is not recognized.
        """
        entity_class = self._get_entity_class(entity_name)
        return entity_class.PRIMARY_KEY_FIELD


# Module-level singleton for convenience
_entity_factory: EntityFactory | None = None


def get_entity_factory() -> EntityFactory:
    """Get singleton instance of EntityFactory.

    Returns:
        Shared EntityFactory instance.
    """
    global _entity_factory  # noqa: PLW0603
    if _entity_factory is None:
        _entity_factory = EntityFactory()
    return _entity_factory


__all__ = [
    "EntityFactory",
    "get_entity_factory",
]
