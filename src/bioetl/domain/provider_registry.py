"""Registry for provider definitions."""

from __future__ import annotations

from typing import Iterable, Protocol, runtime_checkable

from bioetl.domain.errors import ProviderError
from bioetl.domain.providers import ProviderDefinition, ProviderId

__all__ = [
    "ProviderNotRegisteredError",
    "ProviderRegistryError",
    "ProviderAlreadyRegisteredError",
    "ProviderRegistryABC",
    "MutableProviderRegistryABC",
    "ProviderRegistryLoaderABC",
    "InMemoryProviderRegistry",
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


@runtime_checkable
class ProviderRegistryABC(Protocol):
    """Port defining read access to provider definitions."""

    def get_provider(self, provider_id: ProviderId) -> ProviderDefinition:
        """Fetch provider definition by id."""

    def list_providers(self) -> list[ProviderDefinition]:
        """Return all registered provider definitions."""


@runtime_checkable
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


@runtime_checkable
class ProviderRegistryLoaderABC(Protocol):
    """Loader contract for provider registry definitions."""

    def get_providers(
        self,
        *,
        registry: MutableProviderRegistryABC | None = None,
    ) -> list[ProviderDefinition]:
        """Get provider definitions into registry and return them."""

    def get_registry(
        self, *, registry: MutableProviderRegistryABC | None = None
    ) -> MutableProviderRegistryABC:
        """Populate registry and return it (compatibility helper)."""


class InMemoryProviderRegistry(MutableProviderRegistryABC):
    """In-memory implementation of provider registry."""

    def __init__(self) -> None:
        self._providers: dict[ProviderId, ProviderDefinition] = {}

    def register_provider(self, definition: ProviderDefinition) -> None:
        """Register a provider definition, rejecting duplicates."""
        if definition.id in self._providers:
            raise ProviderAlreadyRegisteredError(definition.id.value)
        self._providers[definition.id] = definition

    def get_provider(self, provider_id: ProviderId) -> ProviderDefinition:
        """Return provider definition by id or raise if missing."""
        try:
            return self._providers[provider_id]
        except KeyError as exc:  # pragma: no cover - defensive
            raise ProviderNotRegisteredError(provider_id.value) from exc

    def list_providers(self) -> list[ProviderDefinition]:
        """List all registered provider definitions."""
        return list(self._providers.values())

    def reset_provider_registry(self) -> None:
        """Clear registry content."""
        self._providers.clear()

    def restore_provider_registry(
        self, definitions: Iterable[ProviderDefinition]
    ) -> None:
        """Replace registry content with provided definitions."""
        self.reset_provider_registry()
        for definition in definitions:
            self._providers[definition.id] = definition


def default_provider_registry() -> ProviderRegistryABC:
    """Return default provider registry implementation."""

    return InMemoryProviderRegistry()


def default_mutable_provider_registry() -> MutableProviderRegistryABC:
    """Return default mutable provider registry implementation."""

    return InMemoryProviderRegistry()