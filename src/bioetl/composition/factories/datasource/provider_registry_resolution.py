"""Shared provider-registry resolution helpers for datasource factories."""

from __future__ import annotations

from typing import cast

from bioetl.composition.providers.provider_registry import (
    ProviderDataSourceAccessProtocol,
    resolve_provider_registry,
)


def resolve_datasource_provider_registry(
    provider_registry: ProviderDataSourceAccessProtocol | None = None,
) -> ProviderDataSourceAccessProtocol:
    """Resolve and initialize the registry used by datasource factory helpers."""
    resolved_registry = resolve_provider_registry(
        provider_registry,
        ensure_ready=True,
    )
    return cast("ProviderDataSourceAccessProtocol", resolved_registry)


__all__ = ["resolve_datasource_provider_registry", "resolve_provider_registry"]
