"""Data Source Factory and Registry.

Consolidated module for data source creation and registry.

Contains:
- DataSourceFactory: Abstract Factory for creating data source adapters
- DataSourceRegistry: Backward-compatible facade over ProviderRegistry

Usage:
    >>> from bioetl.composition.factories.data_source_factory import DataSourceFactory
    >>> adapter = DataSourceFactory.create("chembl", http_client=client, logger=logger)

After the registry unification, both classes delegate to ProviderRegistry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from bioetl.composition.providers import (
    DataSourceCreator,
    ProviderRegistry,
    ensure_providers_loaded,
)

if TYPE_CHECKING:
    from bioetl.domain.filter_config import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


# Re-export DataSourceCreator for backward compatibility
__all__ = ["DataSourceCreator", "DataSourceFactory", "DataSourceRegistry"]


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
            """Create a data source for the captured provider name.

            This closure captures the provider name from the outer scope and
            delegates creation to ProviderRegistry.create_data_source().

            Args:
                settings: Application settings for configuration.
                pipeline_config: Pipeline-specific YAML configuration.
                logger: LoggerPort for structured logging.
                filter_config: Optional input filtering configuration.
                metrics: Optional MetricsPort for observability.
                pipeline_name: Pipeline identifier for logging context.

            Returns:
                DataSourcePort implementation for the provider.

            Note:
                This is a backward-compatibility wrapper. For new code, prefer
                using ProviderRegistry.create_data_source() directly.
            """
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
