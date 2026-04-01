"""Shared provider-registry resolution helpers for datasource factories."""

from __future__ import annotations

from bioetl.composition.providers.provider_registry import (
    ProviderRegistry,
    resolve_provider_registry,
)


def resolve_datasource_provider_registry(
    provider_registry: ProviderRegistry | None = None,
) -> ProviderRegistry:
    """Resolve and initialize the registry used by datasource factory helpers."""
    resolved_registry = resolve_provider_registry(
        provider_registry,
        ensure_ready=True,
    )
    return resolved_registry


__all__ = ["resolve_datasource_provider_registry", "resolve_provider_registry"]
