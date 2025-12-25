"""Provider registration system.

Provides unified API for registering data source providers.

Example:
    >>> from bioetl.composition.providers import (
    ...     ProviderRegistry,
    ...     register_provider,
    ...     load_providers,
    ... )
    >>>
    >>> # Загрузка всех провайдеров
    >>> load_providers()
    >>>
    >>> # Получение конфигурации провайдера
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

__all__ = [
    "HttpConfig",
    "ProviderConfig",
    "ProviderRegistry",
    "ensure_providers_loaded",
    "load_providers",
    "register_provider",
]
