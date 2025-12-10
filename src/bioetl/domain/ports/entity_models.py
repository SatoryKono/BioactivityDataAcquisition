"""Port for entity model registry abstraction.

This module defines the abstract interface for entity-to-model mappings,
allowing different implementations (ChEMBL, UniProt, etc.) to provide
their own model registries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class EntityModelRegistryABC(ABC):
    """Abstract interface for entity model registries.

    This port defines the contract for mapping entity type names
    (like "activity", "molecule") to their corresponding Pydantic
    model classes.

    Implementations should be provided by the infrastructure layer
    for each data source (ChEMBL, UniProt, etc.).

    Example:
        >>> class ChemblModelRegistry(EntityModelRegistryABC):
        ...     def get_model(self, entity: str) -> type[BaseModel]:
        ...         return MODELS[entity]
        ...     def is_supported(self, entity: str) -> bool:
        ...         return entity in MODELS
        ...     def supported_entities(self) -> frozenset[str]:
        ...         return frozenset(MODELS.keys())
    """

    @abstractmethod
    def get_model(self, entity: str) -> type[BaseModel]:
        """Get the Pydantic model class for an entity type.

        Args:
            entity: Entity type name (e.g., "activity", "molecule").

        Returns:
            The Pydantic model class for the given entity.

        Raises:
            ValueError: If entity type is not supported.
        """

    @abstractmethod
    def is_supported(self, entity: str) -> bool:
        """Check if an entity type is supported.

        Args:
            entity: Entity type name to check.

        Returns:
            True if entity type has a registered model, False otherwise.
        """

    @abstractmethod
    def supported_entities(self) -> frozenset[str]:
        """Return all supported entity type names.

        Returns:
            Frozen set of all supported entity type names.
        """


__all__ = ["EntityModelRegistryABC"]
