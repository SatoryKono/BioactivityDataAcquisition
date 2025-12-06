"""
Compatibility namespace for legacy imports.

Re-exports provider registry helpers from infrastructure layer.
"""

from bioetl.infrastructure.config.provider_registry_loader import (  # noqa: F401
    DEFAULT_PROVIDERS_REGISTRY_PATH,
    ProviderNotConfiguredError,
    ProviderRegistryError,
    ProviderRegistryFormatError,
    ProviderRegistryNotFoundError,
    clear_provider_registry_cache,
    ensure_provider_known,
)

__all__ = [
    "provider_registry",
    "DEFAULT_PROVIDERS_REGISTRY_PATH",
    "ProviderNotConfiguredError",
    "ProviderRegistryError",
    "ProviderRegistryFormatError",
    "ProviderRegistryNotFoundError",
    "clear_provider_registry_cache",
    "ensure_provider_known",
]

