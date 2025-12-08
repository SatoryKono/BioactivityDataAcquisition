"""Provider registry loader protocol for interfaces layer."""

from __future__ import annotations

from typing import Protocol

from bioetl.domain.provider_registry import MutableProviderRegistryABC
from bioetl.domain.providers import ProviderDefinition


class ProviderRegistryLoaderABC(Protocol):
    """Loader contract for provider registry definitions."""

    def get_providers(
        self, *, registry: MutableProviderRegistryABC | None = None
    ) -> list[ProviderDefinition]:
        """Get provider definitions into registry and return them."""

    def get_registry(
        self, *, registry: MutableProviderRegistryABC | None = None
    ) -> MutableProviderRegistryABC:
        """Populate registry and return it (compatibility helper)."""


__all__ = ["ProviderRegistryLoaderABC"]
