"""Provider registration public API with lazy exports.

The package root preserves historical ``from bioetl.composition.providers import ...``
usage without eagerly importing loader, registry, and registration surfaces
during package initialization.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

_PROVIDER_REGISTRY_MODULE = "bioetl.composition.providers.provider_registry"


if TYPE_CHECKING:
    from bioetl.composition.providers._models import (
        CircuitBreakerConfig as CircuitBreakerConfig,
    )
    from bioetl.composition.providers.decorators import (
        register_provider as register_provider,
    )
    from bioetl.composition.providers.loader import (
        ensure_providers_loaded as ensure_providers_loaded,
        load_providers as load_providers,
    )
    from bioetl.composition.providers.provider_registry import (
        DataSourceCreatorProtocol as DataSourceCreatorProtocol,
        HttpConfig as HttpConfig,
        ProviderConfig as ProviderConfig,
        ProviderRegistry as ProviderRegistry,
        create_provider_registry as create_provider_registry,
        get_default_provider_registry as get_default_provider_registry,
    )
    from bioetl.composition.providers.registration import (
        register_all_providers as register_all_providers,
    )

_PUBLIC_EXPORTS = {
    "CircuitBreakerConfig": (
        "bioetl.composition.providers._models",
        "CircuitBreakerConfig",
    ),
    "DataSourceCreatorProtocol": (
        _PROVIDER_REGISTRY_MODULE,
        "DataSourceCreatorProtocol",
    ),
    "HttpConfig": (
        _PROVIDER_REGISTRY_MODULE,
        "HttpConfig",
    ),
    "ProviderConfig": (
        _PROVIDER_REGISTRY_MODULE,
        "ProviderConfig",
    ),
    "ProviderRegistry": (
        _PROVIDER_REGISTRY_MODULE,
        "ProviderRegistry",
    ),
    "create_provider_registry": (
        _PROVIDER_REGISTRY_MODULE,
        "create_provider_registry",
    ),
    "ensure_providers_loaded": (
        "bioetl.composition.providers.loader",
        "ensure_providers_loaded",
    ),
    "get_default_provider_registry": (
        _PROVIDER_REGISTRY_MODULE,
        "get_default_provider_registry",
    ),
    "load_providers": (
        "bioetl.composition.providers.loader",
        "load_providers",
    ),
    "register_all_providers": (
        "bioetl.composition.providers.registration",
        "register_all_providers",
    ),
    "register_provider": (
        "bioetl.composition.providers.decorators",
        "register_provider",
    ),
}

__all__ = [*_PUBLIC_EXPORTS]


def __getattr__(name: str) -> object:
    export = _PUBLIC_EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = export
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
