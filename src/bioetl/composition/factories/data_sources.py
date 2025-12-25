"""DataSourceFactory for creating data source adapters.

Implements Abstract Factory pattern for data sources.
Uses ProviderRegistry for unified provider registration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.composition.providers import ProviderRegistry, ensure_providers_loaded

if TYPE_CHECKING:
    from bioetl.domain.ports import DataSourcePort, LoggerPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings


class DataSourceFactory:
    """Factory for creating data source adapters.

    Uses ProviderRegistry for provider lookup and adapter creation.
    """

    @classmethod
    def create(
        cls,
        provider: str,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: Settings | None = None,
        **kwargs: Any,
    ) -> DataSourcePort:
        """Create a data source adapter.

        Uses ProviderRegistry for provider lookup and adapter creation.

        Args:
            provider: The name of the data provider (e.g., 'chembl', 'pubchem').
            http_client: The shared HTTP client to use (only for adapters that support it).
            logger: LoggerPort instance for structured logging.
            settings: Application settings (for custom creators).
            **kwargs: Additional keyword arguments to pass to the adapter constructor.

        Returns:
            An instance of the requested data source adapter.

        Raises:
            ValueError: If the provider is unknown.
        """
        # Ensure providers are loaded
        ensure_providers_loaded()

        # Validate provider is registered
        if not ProviderRegistry.is_registered(provider):
            available = ", ".join(ProviderRegistry.list_providers())
            raise ValueError(f"Unknown provider: {provider}. Available: {available}")

        # Remove filter_config from kwargs - it's handled by FilteredDataSource wrapper
        adapter_kwargs = {k: v for k, v in kwargs.items() if k != "filter_config"}

        return ProviderRegistry.create_adapter(
            provider,
            http_client=http_client,
            logger=logger,
            settings=settings,
            **adapter_kwargs,
        )

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all available providers.

        Returns:
            Sorted list of registered provider names.
        """
        ensure_providers_loaded()
        return ProviderRegistry.list_providers()
