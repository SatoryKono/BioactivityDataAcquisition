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
    >>> print(config.http_config.rate)
    10.0
"""

from bioetl.composition.providers.decorators import register_provider
from bioetl.composition.providers.loader import (
    ensure_providers_loaded,
    load_providers,
)
from bioetl.composition.providers.provider_registry import (
    HttpConfig,
    ProviderConfig,
    ProviderRegistry,
)
from bioetl.composition.providers.registration import register_all_providers

__all__ = [
    "HttpConfig",
    "ProviderConfig",
    "ProviderRegistry",
    "ensure_providers_loaded",
    "load_providers",
    "register_all_providers",
    "register_provider",
]
