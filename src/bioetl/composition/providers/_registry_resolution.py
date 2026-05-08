"""Canonical provider-registry resolution helpers for composition seams."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypeVar, cast, overload

from bioetl.composition.providers._default_registry import (
    get_default_provider_registry,
)
from bioetl.composition.providers._loading import ensure_provider_registry_loaded
from bioetl.composition.providers._registry_protocols import (
    ProviderDataSourceRegistryProtocol,
    ProviderRegistrarProtocol,
)

if TYPE_CHECKING:
    from bioetl.composition.providers.provider_registry import ProviderRegistry

__all__ = ["resolve_provider_registry"]

RegistryT = TypeVar("RegistryT", bound=ProviderRegistrarProtocol)


@overload
def resolve_provider_registry(
    provider_registry: None = None,
    *,
    ensure_ready: Literal[False] = False,
) -> ProviderRegistry:
    """Resolve default provider registry without forcing readiness."""
    ...


@overload
def resolve_provider_registry(
    provider_registry: ProviderRegistry | None = None,
    *,
    ensure_ready: Literal[True],
) -> ProviderRegistry:
    """Resolve provider registry and guarantee ready/loaded state."""
    ...


@overload
def resolve_provider_registry[RegistryT: ProviderRegistrarProtocol](
    provider_registry: RegistryT,
    *,
    ensure_ready: Literal[False] = False,
) -> RegistryT:
    """Pass through explicit registry implementation without readiness forcing."""
    ...


def resolve_provider_registry(
    provider_registry: ProviderRegistrarProtocol | None = None,
    *,
    ensure_ready: bool = False,
) -> ProviderRegistrarProtocol:
    """Resolve explicit-or-default registry access through one private seam."""
    resolved_registry = (
        provider_registry
        if provider_registry is not None
        else cast(
            "ProviderDataSourceRegistryProtocol",
            get_default_provider_registry(),
        )
    )
    if ensure_ready:
        ensure_provider_registry_loaded(resolved_registry)
    return resolved_registry
