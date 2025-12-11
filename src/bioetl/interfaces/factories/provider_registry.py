"""Provider registry factory for composition root.

This module provides factory functions for creating provider registry instances.
These factories are the single place where infrastructure is imported for DI,
keeping the application layer clean from infrastructure dependencies.
"""

from __future__ import annotations

from bioetl.domain.provider_registry import ProviderRegistryFactory


def create_provider_registry_factory() -> ProviderRegistryFactory:
    """Create the default provider registry factory.

    This is the single place where infrastructure is imported for DI.
    The factory returns a class (not an instance) that can be called
    to create new InMemoryProviderRegistry instances.

    Returns:
        Factory function that creates InMemoryProviderRegistry instances.

    Example:
        >>> factory = create_provider_registry_factory()
        >>> registry = factory()
        >>> registry.register_provider(provider_definition)
    """
    from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry

    return InMemoryProviderRegistry


__all__ = ["create_provider_registry_factory"]
