"""Retained class-level compatibility helpers for the default provider registry.
This module is the private owner of the lazy default registry singleton; use
``_registry_resolution.py`` or explicit injection for new bootstrap logic."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from importlib import import_module
from typing import TYPE_CHECKING, Protocol, Self, TypeVar, cast, overload

if TYPE_CHECKING:
    from bioetl.composition.providers._models import ProviderConfig

R = TypeVar("R")

class _SupportsDefaultRegistry(Protocol):
    @classmethod
    def _get_default(cls) -> Self:
        """Return the lazy default registry instance."""
        ...

class _SupportsProviderStore(Protocol):
    _providers: dict[str, ProviderConfig]

class _SupportsProviderRegistryStore(_SupportsDefaultRegistry, Protocol):
    _store: _SupportsProviderStore

    def register(self, name: str, config: ProviderConfig) -> None: ...

    def is_registered(self, name: str) -> bool:
        """Return whether a provider is registered."""
        ...

    def list_providers(self) -> list[str]:
        """Return registered provider names."""
        ...

    def clear(self) -> None:
        """Clear registered providers."""
        ...

RegistryT = TypeVar("RegistryT", bound=_SupportsDefaultRegistry)
ProviderRegistryT = TypeVar("ProviderRegistryT", bound=_SupportsProviderRegistryStore)

# Compatibility note: architecture guardrails expect the historical singleton
# ownership seam to remain explicit in this private helper.
# _default_provider_registry: ProviderRegistry | None = None
_default_provider_registry: _SupportsProviderRegistryStore | None = None

class DefaultRegistryMethod[R]:
    """Dispatch class access to the lazy default registry and instance access locally."""

    def __init__(self, func: Callable[..., R]) -> None:
        self._func = func
        self.__doc__ = func.__doc__
        self.__name__ = func.__name__

    @overload
    def __get__(
        self,
        obj: RegistryT,
        objtype: type[RegistryT] | None = None,
    ) -> Callable[..., R]: ...

    @overload
    def __get__(
        self,
        obj: None,
        objtype: type[RegistryT],
    ) -> Callable[..., R]: ...

    def __get__(
        self,
        obj: RegistryT | None,
        objtype: type[RegistryT] | None = None,
    ) -> Callable[..., R]:
        if obj is not None:
            target = obj
        else:
            if objtype is None:
                raise AssertionError(
                    "objtype is required for class-level registry access"
                )
            target = objtype._get_default()

        @wraps(self._func)
        def bound(*args: object, **kwargs: object) -> R:
            return self._func(target, *args, **kwargs)

        return bound

class ProvidersDescriptor[ProviderRegistryT: _SupportsProviderRegistryStore]:
    """Expose the default singleton store on class access for compatibility."""

    def __get__(
        self,
        obj: ProviderRegistryT | None,
        objtype: type[ProviderRegistryT],
    ) -> dict[str, ProviderConfig]:
        target = obj if obj is not None else objtype._get_default()
        return target._store._providers

def get_default_provider_registry() -> _SupportsProviderRegistryStore:
    """Return the lazily-created default provider registry singleton."""
    global _default_provider_registry
    if _default_provider_registry is None:
        module = import_module("bioetl.composition.providers.provider_registry")
        registry = cast(_SupportsProviderRegistryStore, module.ProviderRegistry())
        _default_provider_registry = registry
        return registry
    return _default_provider_registry

def register_provider_config_in_default_registry(
    name: str, config: ProviderConfig
) -> None:
    """Register a provider config through the lazy default-registry seam."""
    get_default_provider_registry().register(name, config)
