"""Adapters Factory - unified factory for creating adapters and data sources.

Consolidated from http_client_factory.py, data_sources.py, and data_source_registry.py.
Provides:
- HttpClientFactory: Factory for creating HTTP clients
- DataSourceFactory: Factory for creating data source adapters
- DataSourceRegistry: Registry facade for data source creators
- DataSourceCreator: Type alias for creator functions

Usage:
    >>> from bioetl.composition.factories.adapters_factory import HttpClientFactory
    >>> client = HttpClientFactory.create_for_provider("chembl")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from bioetl.composition.providers import (
    DataSourceCreator,
    ProviderRegistry,
    ensure_providers_loaded,
)
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

if TYPE_CHECKING:
    from bioetl.domain.filter_config import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


# =============================================================================
# HttpClientFactory (from http_client_factory.py)
# =============================================================================


class HttpClientFactory:
    """Factory for creating HTTP clients.

    Uses ProviderRegistry for configuration lookup.
    Ensures consistent rate limiting and circuit breaker settings across providers.
    """

    @classmethod
    def create_for_provider(
        cls, provider: str, settings: Settings | None = None
    ) -> UnifiedHTTPClient:
        """Create a configured HTTP client for the given provider.

        Uses ProviderRegistry for configuration lookup.

        Args:
            provider: Provider name (e.g., 'chembl', 'pubmed')
            settings: Optional settings to override defaults (e.g., API keys)

        Returns:
            UnifiedHTTPClient configured for the provider

        Raises:
            ValueError: If the provider is unknown.
        """
        # Ensure providers are loaded
        ensure_providers_loaded()

        # Validate provider is registered
        if not ProviderRegistry.is_registered(provider):
            available = ", ".join(ProviderRegistry.list_providers())
            raise ValueError(f"Unknown provider: {provider}. Available: {available}")

        return cls._create_from_registry(provider, settings)

    @classmethod
    def _create_from_registry(
        cls, provider: str, settings: Settings | None
    ) -> UnifiedHTTPClient:
        """Create HTTP client using ProviderRegistry configuration.

        Args:
            provider: Provider name
            settings: Application settings

        Returns:
            Configured UnifiedHTTPClient
        """
        http_config = ProviderRegistry.get_http_config(provider)

        if http_config is None:
            # Provider doesn't use shared HTTP client
            # Return default client
            return UnifiedHTTPClient(
                rate_limiter=TokenBucket(rate=5.0, capacity=10),
                circuit_breaker=CircuitBreaker(provider=provider),
            )

        rate = http_config.rate
        capacity = http_config.capacity

        # Apply rate overrides based on settings
        if settings and http_config.rate_overrides:
            for setting_name, override_rate in http_config.rate_overrides.items():
                if cls._check_setting(settings, setting_name):
                    rate = override_rate
                    capacity = int(override_rate * 2)
                    break

        return UnifiedHTTPClient(
            rate_limiter=TokenBucket(rate=rate, capacity=capacity),
            circuit_breaker=CircuitBreaker(provider=provider),
        )

    @classmethod
    def _check_setting(cls, settings: Settings, setting_name: str) -> bool:
        """Check if a setting is present and truthy.

        Args:
            settings: Application settings
            setting_name: Name of the setting to check

        Returns:
            True if setting exists and is truthy
        """
        value = getattr(settings, setting_name, None)
        return value is not None and bool(value)


# =============================================================================
# DataSourceFactory (from data_sources.py)
# =============================================================================


class DataSourceFactory:
    """Factory for creating data source adapters.

    Uses ProviderRegistry for provider lookup and adapter creation.
    Implements Abstract Factory pattern for data sources.
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


# =============================================================================
# DataSourceRegistry (from data_source_registry.py)
# =============================================================================


class DataSourceRegistry:
    """Thin facade over ProviderRegistry for data source creation.

    This class provides backward compatibility for code that used the old
    DataSourceRegistry API. It now delegates to ProviderRegistry for all
    operations.

    Example:
        >>> # Old way (still works)
        >>> creator = DataSourceRegistry.get("chembl")
        >>> data_source = creator(settings, pipeline_config, logger)
        >>>
        >>> # Preferred new way
        >>> data_source = ProviderRegistry.create_data_source(
        ...     "chembl", settings, pipeline_config, logger
        ... )

    Note:
        For new code, prefer using ProviderRegistry.create_data_source() directly.
    """

    # Empty dict - we delegate everything to ProviderRegistry
    _creators: ClassVar[dict[str, DataSourceCreator]] = {}

    @classmethod
    def get(cls, provider: str) -> DataSourceCreator:
        """Get creator function for provider.

        Returns a closure that delegates to ProviderRegistry.create_data_source().

        Args:
            provider: Provider name (e.g., 'chembl', 'pubchem')

        Returns:
            Creator function for the provider

        Raises:
            KeyError: If provider is not registered
        """
        ensure_providers_loaded()

        # Check if provider exists in ProviderRegistry
        if not ProviderRegistry.is_registered(provider):
            available = ", ".join(ProviderRegistry.list_providers())
            raise KeyError(f"Unknown provider: {provider}. Available: {available}")

        # Check if provider has data_source_creator configured
        if not ProviderRegistry.has_data_source_creator(provider):
            raise KeyError(
                f"Provider '{provider}' does not have a data_source_creator. "
                "Ensure it is registered with data_source_creator in registration.py."
            )

        # Return a closure that delegates to ProviderRegistry
        def creator(
            settings: Settings,
            pipeline_config: PipelineYamlConfig,
            logger: LoggerPort,
            filter_config: InputFilterConfig | None = None,
            metrics: MetricsPort | None = None,
            pipeline_name: str = "unknown",
        ) -> DataSourcePort:
            return ProviderRegistry.create_data_source(
                name=provider,
                settings=settings,
                pipeline_config=pipeline_config,
                logger=logger,
                filter_config=filter_config,
                metrics=metrics,
                pipeline_name=pipeline_name,
            )

        return creator

    @classmethod
    def register(cls, provider: str, creator: DataSourceCreator) -> None:
        """Register a new data source creator.

        Note: This method is deprecated. Use ProviderRegistry.register() instead
        with a ProviderConfig that includes data_source_creator.

        Args:
            provider: Provider name
            creator: Creator function
        """
        # For backward compatibility, store locally
        # New registrations should go through ProviderRegistry
        cls._creators[provider] = creator

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered providers.

        Returns providers from ProviderRegistry that have data_source_creator.
        """
        ensure_providers_loaded()
        # Return all providers from ProviderRegistry
        # (they all have data_source_creator after unification)
        return ProviderRegistry.list_providers()

    @classmethod
    def list_keys(cls) -> list[str]:
        """List all registered provider names (unified API).

        Alias for list_providers().
        """
        return cls.list_providers()

    @classmethod
    def contains(cls, key: str) -> bool:
        """Check if provider is registered.

        Args:
            key: Provider name to check

        Returns:
            True if provider is registered and has data_source_creator
        """
        ensure_providers_loaded()
        return ProviderRegistry.has_data_source_creator(key)

    @classmethod
    def clear(cls) -> None:
        """Clear local registrations (for testing).

        Note: This only clears the local _creators dict.
        Use ProviderRegistry.clear() to clear the main registry.
        """
        cls._creators.clear()


# Re-export DataSourceCreator for backward compatibility
__all__ = [
    "DataSourceCreator",
    "DataSourceFactory",
    "DataSourceRegistry",
    "HttpClientFactory",
]
