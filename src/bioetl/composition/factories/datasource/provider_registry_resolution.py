"""Shared provider-registry resolution helpers for datasource factories."""

from __future__ import annotations

from bioetl.composition.providers.provider_registry import (
    ProviderRegistry,
    ensure_provider_registry_ready,
)


def resolve_datasource_provider_registry(
    provider_registry: ProviderRegistry | None = None,
) -> ProviderRegistry:
    """Resolve and initialize the registry used by datasource factory helpers."""
    resolved_registry = (
        provider_registry
        if provider_registry is not None
        else ProviderRegistry._get_default()
    )
    return ensure_provider_registry_ready(resolved_registry)


__all__ = ["resolve_datasource_provider_registry"]
