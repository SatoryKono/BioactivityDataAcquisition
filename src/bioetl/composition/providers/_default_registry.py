"""Private helpers for class-level access to the default provider registry."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Concatenate,
    Generic,
    ParamSpec,
    Protocol,
    TypeVar,
    overload,
)

if TYPE_CHECKING:
    from bioetl.composition.providers._models import ProviderConfig


P = ParamSpec("P")
R = TypeVar("R")
DefaultRegistryT = TypeVar("DefaultRegistryT", bound="_SupportsDefaultRegistry")


class _SupportsDefaultRegistry(Protocol):
    """Protocol for registries exposing a lazy default instance."""

    @classmethod
    def _get_default(
        cls: type[DefaultRegistryT],
    ) -> DefaultRegistryT:
        """Return the lazy default registry instance."""


class _SupportsProviderStore(Protocol):
    """Protocol for provider stores exposing the underlying mapping."""

    _providers: dict[str, ProviderConfig]


class _SupportsProviderRegistryStore(_SupportsDefaultRegistry, Protocol):
    """Protocol for registries exposing a provider store."""

    _store: _SupportsProviderStore


RegistryT = TypeVar("RegistryT", bound=_SupportsDefaultRegistry)
ProviderRegistryT = TypeVar("ProviderRegistryT", bound=_SupportsProviderRegistryStore)


class DefaultRegistryMethod(Generic[RegistryT, P, R]):
    """Dispatch class access to the lazy default registry and instance access locally."""

    def __init__(self, func: Callable[Concatenate[RegistryT, P], R]) -> None:
        self._func = func
        self.__doc__ = func.__doc__
        self.__name__ = func.__name__

    @overload
    def __get__(
        self,
        obj: RegistryT,
        objtype: type[RegistryT] | None = None,
    ) -> Callable[P, R]: ...

    @overload
    def __get__(
        self,
        obj: None,
        objtype: type[RegistryT],
    ) -> Callable[P, R]: ...

    def __get__(
        self,
        obj: RegistryT | None,
        objtype: type[RegistryT] | None = None,
    ) -> Callable[P, R]:
        if obj is not None:
            target = obj
        else:
            if objtype is None:
                raise AssertionError("objtype is required for class-level registry access")
            target = objtype._get_default()

        @wraps(self._func)
        def bound(*args: P.args, **kwargs: P.kwargs) -> R:
            return self._func(target, *args, **kwargs)

        return bound


class ProvidersDescriptor(Generic[ProviderRegistryT]):
    """Expose the default singleton store on class access for compatibility."""

    def __get__(
        self,
        obj: ProviderRegistryT | None,
        objtype: type[ProviderRegistryT],
    ) -> dict[str, ProviderConfig]:
        target = obj if obj is not None else objtype._get_default()
        return target._store._providers
