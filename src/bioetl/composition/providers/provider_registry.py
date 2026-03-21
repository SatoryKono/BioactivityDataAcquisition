"""Provider registry facade over split metadata and creation helpers."""

from __future__ import annotations

import threading
from importlib import import_module
from typing import TYPE_CHECKING

from bioetl.composition.providers._creation import ProviderCreator
from bioetl.composition.providers._default_registry import (
    DefaultRegistryMethod,
    ProvidersDescriptor,
)
from bioetl.composition.providers._models import (
    AdapterCreator,
    DataSourceCreatorProtocol,
    HttpConfig,
    ProviderConfig,
)
from bioetl.composition.providers._store import ProviderStore

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
    "create_provider_registry",
    "ensure_provider_registry_ready",
    "get_default_provider_registry",
]

# Backward-compatible alias kept during the RF-008 terminology cleanup.
DataSourceCreatorPort = DataSourceCreatorProtocol


def _ensure_registry_loaded(registry: ProviderRegistry) -> None:
    """Late-bind registry loading to avoid hard import coupling into providers."""
    loading_module = import_module("bioetl.composition.providers._loading")
    loading_module.ensure_provider_registry_loaded(registry)


class ProviderRegistry:
    """Unified data provider registry (thread-safe, instance-scoped)."""

    def __init__(
        self,
        store: ProviderStore | None = None,
        creator: ProviderCreator | None = None,
    ) -> None:
        self._store = store if store is not None else ProviderStore()
        self._creator = creator if creator is not None else ProviderCreator()
        self._lock = threading.RLock()

    if TYPE_CHECKING:
        _providers: dict[str, ProviderConfig]
    else:
        _providers = ProvidersDescriptor()

    @classmethod
    def _get_default(cls) -> ProviderRegistry:
        return get_default_provider_registry()

    @classmethod
    def ensure_loaded(cls) -> None:
        """Ensure provider registrations are loaded into the registry."""
        _ensure_registry_loaded(cls._get_default())

    @DefaultRegistryMethod
    def register(self, name: str, config: ProviderConfig) -> None:
        """Register a provider (re-registration overwrites, thread-safe)."""
        with self._lock:
            self._store.register(name, config)

    @DefaultRegistryMethod
    def get(self, name: str) -> ProviderConfig:
        """Return provider configuration; raises KeyError if unknown."""
        with self._lock:
            return self._store.get(name)

    @DefaultRegistryMethod
    def is_registered(self, name: str) -> bool:
        """Check whether a provider is registered."""
        with self._lock:
            return self._store.is_registered(name)

    @DefaultRegistryMethod
    def list_providers(self) -> list[str]:
        """Return sorted list of registered provider names."""
        with self._lock:
            return self._store.list_names()

    @DefaultRegistryMethod
    def has_data_source_creator(self, name: str) -> bool:
        """Check whether a provider has a data_source_creator."""
        with self._lock:
            if not self._store.is_registered(name):
                return False
            config = self._store.get(name)
            return self._creator.has_data_source_creator(config)

    @DefaultRegistryMethod
    def clear(self) -> None:
        """Clear the registry (testing only, thread-safe)."""
        with self._lock:
            self._store.clear()

    @DefaultRegistryMethod
    def create_adapter(
        self,
        name: str,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: Settings | None = None,
        **kwargs: object,
    ) -> DataSourcePort:
        """Create a provider adapter instance using registry metadata."""
        with self._lock:
            config = self._store.get(name)
        return self._creator.create_adapter(
            name=name,
            config=config,
            http_client=http_client,
            logger=logger,
            settings=settings,
            **kwargs,
        )

    @DefaultRegistryMethod
    def get_http_config(self, name: str) -> HttpConfig | None:
        """Return the HTTP configuration for a provider, or None."""
        return self.get(name).http_config

    @DefaultRegistryMethod
    def create_data_source(
        self,
        name: str,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort:
        """Create a fully configured data source with filtering support."""
        with self._lock:
            config = self._store.get(name)
        return self._creator.create_data_source(
            name=name,
            config=config,
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            filter_config=filter_config,
            metrics=metrics,
            pipeline_name=pipeline_name,
        )

    @DefaultRegistryMethod
    def build_data_source_creator(self, name: str) -> DataSourceCreatorProtocol:
        """Return a provider-bound data-source creator closure."""
        if self is get_default_provider_registry():
            type(self).ensure_loaded()

        with self._lock:
            config = self._store.get(name)
        self._creator.require_data_source_creator(name=name, config=config)

        def create_data_source_for_provider(
            settings: Settings,
            pipeline_config: PipelineYamlConfig,
            logger: LoggerPort,
            filter_config: InputFilterConfig | None = None,
            metrics: MetricsPort | None = None,
            pipeline_name: str = "unknown",
        ) -> DataSourcePort:
            return self.create_data_source(
                name=name,
                settings=settings,
                pipeline_config=pipeline_config,
                logger=logger,
                filter_config=filter_config,
                metrics=metrics,
                pipeline_name=pipeline_name,
            )

        return self._creator.build_bound_creator(
            name=name,
            create_data_source_fn=create_data_source_for_provider,
        )

    @DefaultRegistryMethod
    def list_keys(self) -> list[str]:
        """List all registered provider names (unified API)."""
        return self.list_providers()

    @DefaultRegistryMethod
    def contains(self, key: str) -> bool:
        """Check if provider is registered (unified API)."""
        return self.is_registered(key)


_default_provider_registry: ProviderRegistry | None = None


def get_default_provider_registry() -> ProviderRegistry:
    """Get the lazily created default global provider registry instance."""
    global _default_provider_registry
    if _default_provider_registry is None:
        _default_provider_registry = ProviderRegistry()
    return _default_provider_registry


def get_default_provider_registrar() -> ProviderRegistry:
    """Return the sanctioned default-registry seam for provider registration."""
    return get_default_provider_registry()


def register_default_provider_config(name: str, config: ProviderConfig) -> None:
    """Register a provider config through the named default-registry seam."""
    get_default_provider_registrar().register(name, config)


def ensure_provider_registry_ready(registry: ProviderRegistry) -> ProviderRegistry:
    """Ensure a provider registry instance is populated before use."""
    _ensure_registry_loaded(registry)
    return registry


def create_provider_registry() -> ProviderRegistry:
    """Create a new isolated provider registry instance."""
    return ProviderRegistry()
