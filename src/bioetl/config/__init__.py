"""
Deprecated compatibility facade for configuration helpers.

Новый код должен использовать ``bioetl.application.config.runtime``.
Модуль сохранён, чтобы старые импорты продолжали работать без изменений.
"""

from warnings import warn

from bioetl.application.config.runtime import build_runtime_config as _build_runtime_config
from bioetl.infrastructure.config.provider_registry_loader import (  # noqa: F401
    DEFAULT_PROVIDERS_REGISTRY_PATH,
    ProviderNotConfiguredError,
    ProviderRegistryError,
    ProviderRegistryFormatError,
    ProviderRegistryNotFoundError,
    clear_provider_registry_cache,
    ensure_provider_known,
)


def build_runtime_config(*args, **kwargs):
    """Deprecated: используйте ``bioetl.application.config.runtime``."""

    warn(
        "bioetl.config.build_runtime_config is deprecated; "
        "use bioetl.application.config.runtime.build_runtime_config instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return _build_runtime_config(*args, **kwargs)


__all__ = [
    "provider_registry",
    "DEFAULT_PROVIDERS_REGISTRY_PATH",
    "ProviderNotConfiguredError",
    "ProviderRegistryError",
    "ProviderRegistryFormatError",
    "ProviderRegistryNotFoundError",
    "clear_provider_registry_cache",
    "ensure_provider_known",
    "build_runtime_config",
]
