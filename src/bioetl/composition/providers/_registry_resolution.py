# basedpyright residual burn-down (shrink-only product surface).
"""Canonical provider-registry resolution helpers for composition seams."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypeVar, overload

from bioetl.composition.providers._registry_protocols import (
    ProviderRegistrarProtocol,
)
from bioetl.composition.providers.provider_registry import (
    resolve_provider_registry as _resolve_provider_registry,
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


def resolve_provider_registry(  # pyright: ignore[reportInconsistentOverload]
    provider_registry: ProviderRegistrarProtocol | None = None,
    *,
    ensure_ready: bool = False,
) -> ProviderRegistrarProtocol:
    """Resolve explicit-or-default registry access through one private seam."""
    return _resolve_provider_registry(provider_registry, ensure_ready=ensure_ready)
