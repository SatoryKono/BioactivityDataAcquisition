"""Loader for provider registry definitions from YAML configuration.

.. deprecated::
    This module is deprecated. Use :mod:`bioetl.infrastructure.config.provider_registry`
    instead. All symbols are re-exported for backward compatibility.

Migration guide:
    Replace imports from:
        ``from bioetl.infrastructure.clients.provider_registry_loader import ...``
    With:
        ``from bioetl.infrastructure.config.provider_registry import ...``
"""

from __future__ import annotations

import warnings

from bioetl.infrastructure.config.provider_registry import (
    DEFAULT_PROVIDERS_CONFIG_PATH,
    ProviderLoaderImpl,
    ProviderRegistryConfig,
    ProviderRegistryConfigNotFoundError,
    ProviderRegistryEntryModel,
    ProviderRegistryLoader,
    ProviderRegistryLoaderError,
    ProviderRegistryValidationError,
    create_provider_loader,
    default_provider_registry_loader,
    get_provider_registry,
)

warnings.warn(
    "bioetl.infrastructure.clients.provider_registry_loader is deprecated. "
    "Use bioetl.infrastructure.config.provider_registry instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "ProviderLoaderImpl",
    "ProviderRegistryLoader",
    "default_provider_registry_loader",
    "create_provider_loader",
    "get_provider_registry",
    "ProviderRegistryLoaderError",
    "ProviderRegistryConfigNotFoundError",
    "ProviderRegistryValidationError",
    "ProviderRegistryEntryModel",
    "ProviderRegistryConfig",
    "DEFAULT_PROVIDERS_CONFIG_PATH",
]
