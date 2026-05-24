"""Provider registration public API with lazy exports.

The package root preserves historical ``from bioetl.composition.providers import ...``
usage without eagerly importing loader, registry, and registration surfaces
during package initialization.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.composition.providers.decorators import register_provider
    from bioetl.composition.providers.loader import (
        ensure_providers_loaded,
        load_providers,
    )
    from bioetl.composition.providers.provider_registry import (
        DataSourceCreatorProtocol,
        HttpConfig,
        ProviderConfig,
        ProviderRegistry,
        create_provider_registry,
        get_default_provider_registry,
    )
    from bioetl.composition.providers.registration import register_all_providers

_PUBLIC_EXPORTS = {
    "DataSourceCreatorProtocol": (
        "bioetl.composition.providers.provider_registry",
        "DataSourceCreatorProtocol",
    ),
    "HttpConfig": (
        "bioetl.composition.providers.provider_registry",
        "HttpConfig",
    ),
    "ProviderConfig": (
        "bioetl.composition.providers.provider_registry",
        "ProviderConfig",
    ),
    "ProviderRegistry": (
        "bioetl.composition.providers.provider_registry",
        "ProviderRegistry",
    ),
    "create_provider_registry": (
        "bioetl.composition.providers.provider_registry",
        "create_provider_registry",
    ),
    "ensure_providers_loaded": (
        "bioetl.composition.providers.loader",
        "ensure_providers_loaded",
    ),
    "get_default_provider_registry": (
        "bioetl.composition.providers.provider_registry",
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

__all__ = list(_PUBLIC_EXPORTS)


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
