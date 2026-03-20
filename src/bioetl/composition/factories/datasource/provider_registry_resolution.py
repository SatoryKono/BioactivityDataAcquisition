"""Shared provider-registry resolution helpers for datasource factories."""

from __future__ import annotations

from bioetl.composition.providers.provider_registry import (
    ProviderRegistry,
    ensure_provider_registry_ready,
    get_default_provider_registry,
)


def resolve_datasource_provider_registry(
    provider_registry: ProviderRegistry | None = None,
) -> ProviderRegistry:
    """Resolve and initialize the registry used by datasource factory helpers."""
    return ensure_provider_registry_ready(
        provider_registry
        if provider_registry is not None
        else get_default_provider_registry()
    )


__all__ = ["resolve_datasource_provider_registry"]
