"""Canonical provider-registry resolution helpers for composition seams."""

from __future__ import annotations

from typing import Literal, TypeVar, cast, overload

from bioetl.composition.providers._registry_protocols import (
    ProviderRegistrarProtocol,
)
from bioetl.composition.providers.provider_registry import (
    ProviderRegistry,
    ensure_provider_registry_ready,
)

__all__ = ["resolve_provider_registry"]

RegistryT = TypeVar("RegistryT", bound=ProviderRegistrarProtocol)


@overload
def resolve_provider_registry(
    provider_registry: None = None,
    *,
    ensure_ready: Literal[False] = False,
) -> ProviderRegistry: ...


@overload
def resolve_provider_registry(
    provider_registry: ProviderRegistry | None = None,
    *,
    ensure_ready: Literal[True],
) -> ProviderRegistry: ...


@overload
def resolve_provider_registry(
    provider_registry: RegistryT,
    *,
    ensure_ready: Literal[False] = False,
) -> RegistryT: ...


def resolve_provider_registry(
    provider_registry: ProviderRegistrarProtocol | None = None,
    *,
    ensure_ready: bool = False,
) -> ProviderRegistrarProtocol:
    """Resolve explicit-or-default registry access through one private seam."""
    resolved_registry = (
        provider_registry
        if provider_registry is not None
        else ProviderRegistry._get_default()
    )
    if ensure_ready:
        return ensure_provider_registry_ready(cast("ProviderRegistry", resolved_registry))
    return resolved_registry
