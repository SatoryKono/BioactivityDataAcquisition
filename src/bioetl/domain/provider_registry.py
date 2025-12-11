"""Domain abstractions for provider registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from bioetl.domain.providers import ProviderDefinition, ProviderId


class ProviderRegistryError(Exception):
    """Base provider registry error."""


class ProviderNotRegisteredError(ProviderRegistryError):
    """Provider not registered error."""

    def __init__(self, provider_id: ProviderId) -> None:
        super().__init__(f"Provider '{provider_id.value}' is not registered")
        self.provider_id = provider_id


class ProviderAlreadyRegisteredError(ProviderRegistryError):
    """Provider already registered error."""

    def __init__(self, provider_id: ProviderId) -> None:
        super().__init__(f"Provider '{provider_id.value}' is already registered")
        self.provider_id = provider_id


class ProviderRegistryABC(ABC):
    """Abstract base class for provider registry."""

    @abstractmethod
    def register_provider(self, definition: ProviderDefinition) -> None:
        """Register provider in registry."""

    @abstractmethod
    def get_provider(self, provider_id: ProviderId) -> ProviderDefinition:
        """Get provider definition by identifier."""

    @abstractmethod
    def list_providers(self) -> list[ProviderDefinition]:
        """Return list of all registered providers."""

    @abstractmethod
    def reset_provider_registry(self) -> None:
        """Clear the provider registry."""

    @abstractmethod
    def restore_provider_registry(self, definitions: list[ProviderDefinition]) -> None:
        """Restore registry from list of definitions."""


@runtime_checkable
class ProviderRegistryLoaderABC(Protocol):
    """Protocol for provider registry loader."""

    def get_providers(
        self, *, registry: ProviderRegistryABC | None = None
    ) -> list[ProviderDefinition]:
        """Load providers from configuration and register them."""

    def get_registry(
        self, *, registry: ProviderRegistryABC | None = None
    ) -> ProviderRegistryABC:
        """Load providers and return populated registry."""


# Global registry instance
_PROVIDER_REGISTRY: ProviderRegistryABC | None = None


def set_provider_registry(registry: ProviderRegistryABC) -> None:
    """Sets the global provider registry instance.

    This should be called by the application entry point or configuration loader
    to inject the concrete implementation (Dependency Injection).
    """
    global _PROVIDER_REGISTRY
    _PROVIDER_REGISTRY = registry


def get_provider_registry() -> ProviderRegistryABC:
    """Access point for the provider registry.

    Returns the global registry instance.
    Raises RuntimeError if the registry has not been initialized.
    """
    if _PROVIDER_REGISTRY is None:
        raise RuntimeError(
            "Provider registry has not been initialized. "
            "Call set_provider_registry() with a concrete implementation first."
        )
    return _PROVIDER_REGISTRY


# Backward compatibility alias
def default_provider_registry() -> ProviderRegistryABC:
    """DEPRECATED: Use get_provider_registry() instead."""
    return get_provider_registry()


def __getattr__(name: str) -> Any:
    """Lazy import for backward compatibility."""
    if name == "InMemoryProviderRegistry":
        raise ImportError(
            "InMemoryProviderRegistry is no longer available in bioetl.domain. "
            "Import it from bioetl.infrastructure.provider_registry instead."
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Domain abstractions
    "ProviderRegistryABC",
    "ProviderRegistryLoaderABC",
    # Domain errors
    "ProviderRegistryError",
    "ProviderNotRegisteredError",
    "ProviderAlreadyRegisteredError",
    # Factory function
    "get_provider_registry",
    "set_provider_registry",
    # Backward compatibility
    "default_provider_registry",
]
