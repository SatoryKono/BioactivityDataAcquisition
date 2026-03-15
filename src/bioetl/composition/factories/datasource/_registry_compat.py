"""Internal helpers for legacy DataSourceRegistry access."""

from __future__ import annotations

from typing import ClassVar

from bioetl.composition.providers._models import DataSourceCreatorProtocol
from bioetl.composition.providers.provider_registry import ProviderRegistry

__all__ = ["DataSourceRegistry", "_build_data_source_creator"]


def _build_data_source_creator(provider: str) -> DataSourceCreatorProtocol:
    """Build a provider-bound data-source creator callback."""
    return ProviderRegistry.build_data_source_creator(provider)


class DataSourceRegistry:
    """Thin facade over ProviderRegistry for legacy data source creation APIs."""

    _creators: ClassVar[dict[str, DataSourceCreatorProtocol]] = {}

    @classmethod
    def get(cls, provider: str) -> DataSourceCreatorProtocol:
        """Get creator function for provider."""
        return _build_data_source_creator(provider)

    @classmethod
    def list_providers(cls) -> list[str]:
        """List providers that expose data-source creators."""
        ProviderRegistry.ensure_loaded()
        return ProviderRegistry.list_providers()

    @classmethod
    def list_keys(cls) -> list[str]:
        """Alias for list_providers()."""
        return cls.list_providers()

    @classmethod
    def contains(cls, key: str) -> bool:
        """Check if provider is registered and has a data-source creator."""
        ProviderRegistry.ensure_loaded()
        return ProviderRegistry.has_data_source_creator(key)

    @classmethod
    def clear(cls) -> None:
        """Clear local registrations retained only for compatibility tests."""
        cls._creators.clear()
