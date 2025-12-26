"""Registry for data source creators.

This module provides backward-compatible access to data source creation
through DataSourceRegistry, which now delegates to ProviderRegistry.

After the registry unification, the actual creator functions live in
bioetl.composition.providers.registration module. This module serves as
a thin facade for backward compatibility.

Note: New code should prefer using ProviderRegistry.create_data_source()
directly for better clarity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

# Re-export DataSourceCreator from ProviderRegistry for backward compatibility
from bioetl.composition.providers import (
    DataSourceCreator,
    ProviderRegistry,
    ensure_providers_loaded,
)

if TYPE_CHECKING:
    from bioetl.domain.filter_config import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

# Re-export for backward compatibility
__all__ = ["DataSourceCreator", "DataSourceRegistry"]


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
