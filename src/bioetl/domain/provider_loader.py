"""Provider loader protocol aliases for backward compatibility."""

from __future__ import annotations

from bioetl.interfaces.provider_registry.contracts import ProviderRegistryLoaderABC

# Backward-compatible alias.
ProviderLoaderProtocol = ProviderRegistryLoaderABC

__all__ = ["ProviderLoaderProtocol", "ProviderRegistryLoaderABC"]
