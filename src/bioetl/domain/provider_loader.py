"""Provider loader protocol aliases for backward compatibility."""

from __future__ import annotations

from bioetl.domain.provider_registry import ProviderRegistryLoaderABC

# Backward-compatible alias.
ProviderLoaderProtocol = ProviderRegistryLoaderABC

__all__ = ["ProviderLoaderProtocol", "ProviderRegistryLoaderABC"]
