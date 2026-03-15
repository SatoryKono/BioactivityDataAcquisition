"""Provider registry facade over split metadata and creation helpers.

Centralizes the public registry API while delegating provider metadata models,
registry-store helpers, and adapter/data-source creation logic to internal
submodules. This keeps the canonical import path stable without forcing future
provider additions through one monolithic implementation file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from bioetl.composition.providers._creation import (
    create_provider_adapter,
    create_provider_data_source,
    provider_has_data_source_creator,
)
from bioetl.composition.providers._models import (
    AdapterCreator,
    DataSourceCreatorProtocol,
    HttpConfig,
    ProviderConfig,
)
from bioetl.composition.providers._store import (
    get_provider_config,
    is_provider_registered,
    list_provider_names,
    register_provider_config,
)

if TYPE_CHECKING:
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


__all__ = [
    "AdapterCreator",
    "DataSourceCreatorProtocol",
    "HttpConfig",
    "ProviderConfig",
    "ProviderRegistry",
]


# Backward-compatible alias kept during the RF-008 terminology cleanup.
DataSourceCreatorPort = DataSourceCreatorProtocol


class ProviderRegistry:
    """Unified data provider registry.

    Centralizes:
    - Provider adapter registration
    - HTTP client configuration
    - Adapter instance creation

    Example:
        >>> from bioetl.composition.providers import ProviderRegistry, register_provider
        >>>
        >>> @register_provider("mydb", http_rate=10.0)
        ... class MyDBAdapter:
        ...     pass
        >>>
        >>> adapter = ProviderRegistry.create_adapter("mydb", http_client=client)
    """

    _providers: ClassVar[dict[str, ProviderConfig]] = {}

    @classmethod
    def ensure_loaded(cls) -> None:
        """Ensure provider registrations are loaded into the registry."""
        from bioetl.composition.providers.loader import ensure_providers_loaded

        ensure_providers_loaded()

    @classmethod
    def register(cls, name: str, config: ProviderConfig) -> None:
        """Register a provider (re-registration overwrites)."""
        register_provider_config(cls._providers, name, config)

    @classmethod
    def get(cls, name: str) -> ProviderConfig:
        """Return provider configuration; raises KeyError if unknown."""
        return get_provider_config(cls._providers, name)

    @classmethod
    def build_data_source_creator(cls, name: str) -> DataSourceCreatorProtocol:
        """Return a provider-bound data-source creator closure."""
        cls.ensure_loaded()

        if not cls.is_registered(name):
            available = ", ".join(cls.list_providers())
            raise KeyError(f"Unknown provider: {name}. Available: {available}")

        if not cls.has_data_source_creator(name):
            raise KeyError(
                f"Provider '{name}' does not have a data_source_creator. "
                "Ensure it is registered with data_source_creator in registration.py."
            )

        def creator(
            settings: Settings,
            pipeline_config: PipelineYamlConfig,
            logger: LoggerPort,
            filter_config: InputFilterConfig | None = None,
            metrics: MetricsPort | None = None,
            pipeline_name: str = "unknown",
        ) -> DataSourcePort:
            """Create a data source for the captured provider name."""
            return cls.create_data_source(
                name=name,
                settings=settings,
                pipeline_config=pipeline_config,
                logger=logger,
                filter_config=filter_config,
                metrics=metrics,
                pipeline_name=pipeline_name,
            )

        return creator

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check whether a provider is registered."""
        return is_provider_registered(cls._providers, name)

    @classmethod
    def create_adapter(
        cls,
        name: str,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: Settings | None = None,
        **kwargs: object,
    ) -> DataSourcePort:
        """Create a provider adapter instance using registry metadata."""
        return create_provider_adapter(
            name=name,
            config=cls.get(name),
            http_client=http_client,
            logger=logger,
            settings=settings,
            **kwargs,
        )

    @classmethod
    def get_http_config(cls, name: str) -> HttpConfig | None:
        """Return the HTTP configuration for a provider, or None."""
        return cls.get(name).http_config

    @classmethod
    def create_data_source(
        cls,
        name: str,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort:
        """Create a fully configured data source with filtering support."""
        return create_provider_data_source(
            name=name,
            config=cls.get(name),
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            filter_config=filter_config,
            metrics=metrics,
            pipeline_name=pipeline_name,
        )

    @classmethod
    def has_data_source_creator(cls, name: str) -> bool:
        """Check whether a provider has a data_source_creator."""
        if not cls.is_registered(name):
            return False
        return provider_has_data_source_creator(cls.get(name))

    @classmethod
    def list_providers(cls) -> list[str]:
        """Return sorted list of registered provider names."""
        return list_provider_names(cls._providers)

    @classmethod
    def clear(cls) -> None:
        """Clear the registry. Used for testing."""
        cls._providers.clear()
