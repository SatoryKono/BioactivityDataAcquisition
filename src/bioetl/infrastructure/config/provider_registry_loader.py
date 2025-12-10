"""Infrastructure loader for provider registry configuration.

.. deprecated::
    This module is deprecated. Use :mod:`bioetl.infrastructure.config.provider_registry`
    instead. All symbols are re-exported for backward compatibility.

Migration guide:
    Replace imports from:
        ``from bioetl.infrastructure.config.provider_registry_loader import ...``
    With:
        ``from bioetl.infrastructure.config.provider_registry import ...``
"""

from __future__ import annotations

import warnings

from bioetl.infrastructure.config.provider_registry import (
    DEFAULT_PROVIDERS_REGISTRY_PATH,
    ProviderNotConfiguredError,
    ProviderRegistryConfig as ProviderRegistryModel,
    ProviderRegistryEntryConfig,
    ProviderRegistryError,
    ProviderRegistryFormatError,
    ProviderRegistryNotFoundError,
    clear_provider_registry_cache,
    ensure_provider_known,
)

warnings.warn(
    "bioetl.infrastructure.config.provider_registry_loader is deprecated. "
    "Use bioetl.infrastructure.config.provider_registry instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "DEFAULT_PROVIDERS_REGISTRY_PATH",
    "ProviderNotConfiguredError",
    "ProviderRegistryError",
    "ProviderRegistryFormatError",
    "ProviderRegistryNotFoundError",
    "clear_provider_registry_cache",
    "ensure_provider_known",
    # Deprecated aliases
    "ProviderRegistryModel",
    "ProviderRegistryEntryConfig",
]
