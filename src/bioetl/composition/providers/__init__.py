"""Provider registration system.

Provides unified API for registering data source providers.

Example:
    >>> from bioetl.composition.providers import (
    ...     ProviderRegistry,
    ...     load_providers,
    ...     register_all_providers,
    ... )
    >>>
    >>> # Load all providers
    >>> load_providers()
    >>>
    >>> # Get provider configuration
    >>> config = ProviderRegistry.get("chembl")
    >>> config.http_config.rate
    10.0
"""
from __future__ import annotations

from bioetl.composition.providers.decorators import register_provider
from bioetl.composition.providers.loader import (
    ensure_providers_loaded,
    load_providers,
)
from bioetl.composition.providers.provider_registry import (
    DataSourceCreatorPort,
    HttpConfig,
    ProviderConfig,
    ProviderRegistry,
)
from bioetl.composition.providers.registration import register_all_providers

__all__ = [
    "DataSourceCreatorPort",
    "HttpConfig",
    "ProviderConfig",
    "ProviderRegistry",
    "ensure_providers_loaded",
    "load_providers",
    "register_all_providers",
    "register_provider",
]
