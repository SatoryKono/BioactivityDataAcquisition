"""Provider registry facade. Retained compatibility obligations are intentionally narrow:"""

from __future__ import annotations

import threading
from functools import partial
from importlib import import_module
from typing import TYPE_CHECKING, cast

from bioetl.composition.providers._creation import (
    ProviderCreator,
    ProviderDataSourceCreationRequest,
)
from bioetl.composition.providers._default_registry import (
    DefaultRegistryMethod,
    ProvidersDescriptor,
    get_default_provider_registry,
)
from bioetl.composition.providers._default_registry import (
    register_provider_config_in_default_registry as register_default_provider_config,
)
from bioetl.composition.providers._models import (
    AdapterCreatorProtocol,
    DataSourceCreatorProtocol,
    HttpConfig,
    ProviderConfig,
    ProviderSettingsProtocol,
)
from bioetl.composition.providers._registry_protocols import (
    ProviderDataSourceAccessProtocol,
    ProviderRegistrarProtocol,
)
from bioetl.composition.providers._store import ProviderStore

if TYPE_CHECKING:
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "AdapterCreatorProtocol",
    "DataSourceCreatorProtocol",
    "HttpConfig",
    "ProviderConfig",
    "ProviderDataSourceAccessProtocol",
    "ProviderRegistrarProtocol",
    "ProviderRegistry",
    "ProviderSettingsProtocol",
    "create_provider_registry",
    "ensure_provider_registry_ready",
    "get_default_provider_registry",
    "register_default_provider_config",
    "resolve_provider_registry",
]


def _ensure_registry_loaded(registry: ProviderRegistrarProtocol) -> None:
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
        return cast("ProviderRegistry", get_default_provider_registry())

    def _get_registered_config(
        self,
        name: str,
        *,
        allow_missing: bool = False,
    ) -> ProviderConfig | None:
        with self._lock:
            if allow_missing and not self._store.is_registered(name):
                return None
            return self._store.get(name)

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
        config = self._get_registered_config(name, allow_missing=True)
        if config is None:
            return False
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
        settings: ProviderSettingsProtocol | None = None,
        **kwargs: object,
    ) -> DataSourcePort:
        """Create a provider adapter instance using registry metadata."""
        config = self._get_registered_config(name)
        assert config is not None
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
        settings: ProviderSettingsProtocol,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort:
        """Create a fully configured data source with filtering support."""
        config = self._get_registered_config(name)
        assert config is not None
        return self._creator.create_data_source(
            ProviderDataSourceCreationRequest(
                name=name,
                config=config,
                settings=settings,
                pipeline_config=pipeline_config,
                logger=logger,
                filter_config=filter_config,
                metrics=metrics,
                pipeline_name=pipeline_name,
            )
        )

    @DefaultRegistryMethod
    def build_data_source_creator(self, name: str) -> DataSourceCreatorProtocol:
        """Return a provider-bound data-source creator closure."""
        if self is type(self)._get_default():
            type(self).ensure_loaded()

        config = self._get_registered_config(name)
        assert config is not None
        self._creator.require_data_source_creator(name=name, config=config)
        return self._creator.build_bound_creator(
            name=name,
            create_data_source_fn=partial(self.create_data_source, name=name),
        )

    @DefaultRegistryMethod
    def list_keys(self) -> list[str]:
        """List all registered provider names (unified API)."""
        return self.list_providers()

    @DefaultRegistryMethod
    def contains(self, key: str) -> bool:
        """Check if provider is registered (unified API)."""
        return self.is_registered(key)


def ensure_provider_registry_ready(
    registry: ProviderRegistrarProtocol,
) -> ProviderRegistrarProtocol:
    """Ensure a provider registry instance is populated before use.

    This remains the sanctioned bootstrap seam for callers that need an
    initialized registry instance without importing provider loading internals.
    """
    _ensure_registry_loaded(registry)
    return registry


def resolve_provider_registry(
    provider_registry: ProviderRegistrarProtocol | None = None,
    *,
    ensure_ready: bool = False,
) -> ProviderRegistrarProtocol:
    """Resolve explicit-or-default registry access through a public seam."""
    resolved_registry = (
        provider_registry
        if provider_registry is not None
        else cast("ProviderRegistrarProtocol", get_default_provider_registry())
    )
    if ensure_ready:
        return ensure_provider_registry_ready(resolved_registry)
    return resolved_registry


def create_provider_registry() -> ProviderRegistry:
    """Create a new isolated provider registry instance."""
    return ProviderRegistry()
