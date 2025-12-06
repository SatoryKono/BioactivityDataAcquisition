"""Registry for provider definitions."""

from __future__ import annotations

from typing import Iterable, Protocol

from bioetl.domain.errors import ProviderError
from bioetl.domain.providers import ProviderDefinition, ProviderId

__all__ = [
    "ProviderNotRegisteredError",
    "ProviderRegistryError",
    "ProviderAlreadyRegisteredError",
    "ProviderRegistryABC",
    "MutableProviderRegistryABC",
    "InMemoryProviderRegistry",
    "register_provider",
    "get_provider",
    "list_providers",
    "reset_provider_registry",
    "restore_provider_registry",
]


class ProviderRegistryError(ProviderError):
    """Base class for provider registry errors."""

    def __init__(self, provider: str, message: str) -> None:
        super().__init__(provider=provider, message=message)


class ProviderNotRegisteredError(ProviderRegistryError):
    """Raised when provider is not registered in the registry."""

    def __init__(self, provider: str) -> None:
        super().__init__(provider, f"Provider '{provider}' is not registered")


class ProviderAlreadyRegisteredError(ProviderRegistryError):
    """Raised when attempting to register a duplicate provider id."""

    def __init__(self, provider: str) -> None:
        super().__init__(provider, f"Provider '{provider}' already registered")


class ProviderRegistryABC(Protocol):
    """Port defining read access to provider definitions."""

    def get_provider(self, provider_id: ProviderId) -> ProviderDefinition:
        """Fetch provider definition by id."""

    def list_providers(self) -> list[ProviderDefinition]:
        """Return all registered provider definitions."""


class MutableProviderRegistryABC(ProviderRegistryABC, Protocol):
    """Mutable port for registering provider definitions."""

    def register_provider(self, definition: ProviderDefinition) -> None:
        """Register a provider definition."""

    def reset_provider_registry(self) -> None:
        """Clear registry content (used for tests)."""

    def restore_provider_registry(
        self, definitions: Iterable[ProviderDefinition]
    ) -> None:
        """Restore registry from supplied definitions."""


class InMemoryProviderRegistry(MutableProviderRegistryABC):
    """In-memory implementation of provider registry."""

    def __init__(self) -> None:
        self._providers: dict[ProviderId, ProviderDefinition] = {}

    def register_provider(self, definition: ProviderDefinition) -> None:
        if definition.id in self._providers:
            raise ProviderAlreadyRegisteredError(definition.id.value)
        self._providers[definition.id] = definition

    def get_provider(self, provider_id: ProviderId) -> ProviderDefinition:
        try:
            return self._providers[provider_id]
        except KeyError as exc:  # pragma: no cover - defensive
            raise ProviderNotRegisteredError(provider_id.value) from exc

    def list_providers(self) -> list[ProviderDefinition]:
        return list(self._providers.values())

    def reset_provider_registry(self) -> None:
        self._providers.clear()

    def restore_provider_registry(
        self, definitions: Iterable[ProviderDefinition]
    ) -> None:
        self.reset_provider_registry()
        for definition in definitions:
            self._providers[definition.id] = definition


_registry: MutableProviderRegistryABC = InMemoryProviderRegistry()


def register_provider(definition: ProviderDefinition) -> None:
    """Register provider definition in the default in-memory registry."""
    _registry.register_provider(definition)


def get_provider(provider_id: ProviderId) -> ProviderDefinition:
    """Return provider definition by id from the default registry."""
    return _registry.get_provider(provider_id)


def list_providers() -> list[ProviderDefinition]:
    """List provider definitions from the default registry."""
    return _registry.list_providers()


def reset_provider_registry() -> None:
    """Clear default registry (utility for tests)."""
    _registry.reset_provider_registry()


def restore_provider_registry(
    definitions: Iterable[ProviderDefinition],
) -> None:
    """Restore default registry from provided definitions."""
    _registry.restore_provider_registry(definitions)
