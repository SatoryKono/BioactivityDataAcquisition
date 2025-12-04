"""Registry for provider definitions."""

from __future__ import annotations

from typing import Iterable

from bioetl.core.providers import ProviderDefinition, ProviderId
from bioetl.domain.errors import ProviderError

__all__ = [
    "ProviderNotRegisteredError",
    "ProviderRegistryError",
    "ProviderAlreadyRegisteredError",
    "get_provider",
    "list_providers",
    "register_provider",
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


_PROVIDERS: dict[ProviderId, ProviderDefinition] = {}


def register_provider(definition: ProviderDefinition) -> None:
    """Register provider definition in the registry."""

    if definition.id in _PROVIDERS:
        raise ProviderAlreadyRegisteredError(definition.id.value)
    _PROVIDERS[definition.id] = definition


def get_provider(provider_id: ProviderId) -> ProviderDefinition:
    """Get provider definition by id."""

    try:
        return _PROVIDERS[provider_id]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ProviderNotRegisteredError(provider_id.value) from exc


def list_providers() -> list[ProviderDefinition]:
    """List all registered provider definitions."""

    return list(_PROVIDERS.values())


def reset_provider_registry() -> None:
    """Clear registry (intended for test isolation)."""

    _PROVIDERS.clear()


def restore_provider_registry(definitions: Iterable[ProviderDefinition]) -> None:
    """Restore registry to provided definitions (used in tests)."""

    reset_provider_registry()
    for definition in definitions:
        _PROVIDERS[definition.id] = definition
