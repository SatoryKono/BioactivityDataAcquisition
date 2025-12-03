"""Typed registry for provider definitions."""

from __future__ import annotations

from typing import Iterable

from bioetl.core.providers import ProviderDefinition, ProviderId

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


class ProviderRegistryError(RuntimeError):
    """Base class for provider registry errors."""


class ProviderNotRegisteredError(ProviderRegistryError):
    """Raised when provider is not registered in the registry."""


class ProviderAlreadyRegisteredError(ProviderRegistryError):
    """Raised when attempting to register a duplicate provider id."""


_registry: dict[ProviderId, ProviderDefinition] = {}


def register_provider(definition: ProviderDefinition) -> None:
    """Register provider definition in the registry."""

    if definition.id in _registry:
        raise ProviderAlreadyRegisteredError(
            f"Provider '{definition.id.value}' already registered"
        )
    _registry[definition.id] = definition


def get_provider(provider_id: ProviderId) -> ProviderDefinition:
    """Get provider definition by id."""

    try:
        return _registry[provider_id]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ProviderNotRegisteredError(
            f"Provider '{provider_id.value}' is not registered"
        ) from exc


def list_providers() -> list[ProviderDefinition]:
    """List all registered provider definitions."""

    return list(_registry.values())


def reset_provider_registry() -> None:
    """Clear registry (intended for test isolation)."""

    _registry.clear()


def restore_provider_registry(definitions: Iterable[ProviderDefinition]) -> None:
    """Restore registry to provided definitions (used in tests)."""

    reset_provider_registry()
    for definition in definitions:
        _registry[definition.id] = definition
