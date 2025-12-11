"""Domain abstractions for provider registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Protocol, runtime_checkable
import warnings

from bioetl.domain.providers import ProviderDefinition, ProviderId

# Type alias for factory function that creates empty provider registry instances.
# Used for dependency injection in application layer to avoid
# direct infrastructure imports.
ProviderRegistryFactory = Callable[[], "ProviderRegistryABC"]


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


def __getattr__(name: str) -> Any:
    """Lazy import for backward compatibility with deprecated functions."""
    if name == "InMemoryProviderRegistry":
        raise ImportError(
            "InMemoryProviderRegistry is no longer available in bioetl.domain. "
            "Import it from bioetl.infrastructure.provider_registry instead."
        )

    # Handle deprecated global state functions - redirect to infrastructure
    if name in (
        "set_provider_registry",
        "get_provider_registry",
        "default_provider_registry",
    ):
        warnings.warn(
            (
                f"{name}() has been removed from bioetl.domain.provider_registry. "
                "Use dependency injection through "
                "CompositionRoot.get_provider_registry() or "
                "bioetl.infrastructure.provider_registry."
                "create_empty_provider_registry() instead."
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        raise AttributeError(
            (
                f"{name}() has been removed. "
                "Use CompositionRoot.get_provider_registry() "
                "for DI-based registry access."
            )
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
    # Type aliases for DI
    "ProviderRegistryFactory",
]
