from __future__ import annotations

from typing import Protocol

from bioetl.domain.provider_registry import ProviderRegistryLoaderABC

# Backward-compatible alias.
ProviderLoaderProtocol = ProviderRegistryLoaderABC

__all__ = ["ProviderLoaderProtocol", "ProviderRegistryLoaderABC"]

