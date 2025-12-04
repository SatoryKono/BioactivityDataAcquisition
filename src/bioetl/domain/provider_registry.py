"""Compatibility wrapper for provider registry."""

from bioetl.core.provider_registry import (
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
