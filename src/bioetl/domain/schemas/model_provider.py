"""Abstract provider for raw API models.

This module defines the abstract interface for providers that supply
raw API models for different data sources. This enables flexible
registration of model providers without hardcoding specific models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from pydantic import BaseModel


class RawModelProviderABC(ABC):
    """Abstract provider for raw API models.

    Implementations provide access to Pydantic models that represent
    raw API responses from external data sources.

    This abstraction enables:
    - Lazy loading of models
    - Registration of models from different sources
    - Testability through mock providers

    Example:
        >>> provider: RawModelProviderABC = ChemblRawModelProvider()
        >>> activity_model = provider.get_model("activity")
        >>> validated = activity_model(**raw_response)
    """

    @abstractmethod
    def get_model(self, entity_name: str) -> Type["BaseModel"]:
        """Get raw model class by entity name.

        Args:
            entity_name: Name of the entity (e.g., "activity", "assay").

        Returns:
            Pydantic model class for the entity.

        Raises:
            KeyError: If no model exists for the entity name.
        """
        ...

    @abstractmethod
    def list_entities(self) -> list[str]:
        """List all available entity names.

        Returns:
            List of entity names supported by this provider.
        """
        ...

    @abstractmethod
    def supports(self, entity_name: str) -> bool:
        """Check if provider supports given entity.

        Args:
            entity_name: Entity name to check.

        Returns:
            True if entity is supported.
        """
        ...

    def get_model_safe(self, entity_name: str) -> Type["BaseModel"] | None:
        """Get model without raising exception.

        Args:
            entity_name: Name of the entity.

        Returns:
            Model class or None if not found.
        """
        if self.supports(entity_name):
            return self.get_model(entity_name)
        return None


class CompositeModelProvider(RawModelProviderABC):
    """Composite provider that delegates to multiple providers.

    Useful for combining models from multiple sources into a single
    provider interface.

    Example:
        >>> composite = CompositeModelProvider([
        ...     ChemblRawModelProvider(),
        ...     PubchemRawModelProvider(),
        ... ])
        >>> model = composite.get_model("activity")  # Tries each provider
    """

    def __init__(self, providers: list[RawModelProviderABC]) -> None:
        """Initialize with list of providers.

        Args:
            providers: List of providers to delegate to.
        """
        self._providers = providers

    def get_model(self, entity_name: str) -> Type["BaseModel"]:
        """Get model from first provider that supports it."""
        for provider in self._providers:
            if provider.supports(entity_name):
                return provider.get_model(entity_name)
        raise KeyError(f"No provider supports entity: {entity_name}")

    def list_entities(self) -> list[str]:
        """List all entities from all providers."""
        entities: set[str] = set()
        for provider in self._providers:
            entities.update(provider.list_entities())
        return sorted(entities)

    def supports(self, entity_name: str) -> bool:
        """Check if any provider supports entity."""
        return any(p.supports(entity_name) for p in self._providers)


__all__ = [
    "CompositeModelProvider",
    "RawModelProviderABC",
]
