"""Typed registry for provider definitions (legacy path)."""

from bioetl.domain.provider_registry import (  # noqa: F401
    ProviderAlreadyRegisteredError,
    ProviderNotRegisteredError,
    ProviderRegistryError,
    get_provider,
    list_providers,
    register_provider,
    reset_provider_registry,
    restore_provider_registry,
)

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
