"""Provider registry facade over split metadata and creation helpers.

Centralizes the public registry API while delegating provider metadata models,
registry-store helpers, and adapter/data-source creation logic to internal
submodules.  Instance-scoped design (RF-001) mirrors PipelineRegistry: each
instance holds its own ``_providers`` dict guarded by ``threading.RLock()``.
A lazy default singleton preserves backward compatibility for all existing
``@classmethod`` callsites.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

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
    "create_provider_registry",
    "get_default_provider_registry",
]

# Backward-compatible alias kept during the RF-008 terminology cleanup.
DataSourceCreatorPort = DataSourceCreatorProtocol


class ProviderRegistry:
    """Unified data provider registry (thread-safe, instance-scoped).

    Each instance holds its own ``_providers`` dict protected by RLock.
    Classmethods delegate to a lazy default singleton, preserving all
    existing ``ProviderRegistry.method()`` callsites unchanged.

    For test isolation, create a new instance via ``create_provider_registry()``.
    """

    def __init__(self) -> None:
        self._providers: dict[str, ProviderConfig] = {}  # type: ignore[no-redef]
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Backward-compatible class-level _providers access (used by tests).
    # Non-data descriptor: instance attrs shadow it automatically.
    # ------------------------------------------------------------------

    class _ProvidersDescriptor:
        """Expose the default singleton's _providers on class-level access."""

        def __get__(
            self, obj: ProviderRegistry | None, objtype: type[ProviderRegistry]
        ) -> dict[str, ProviderConfig]:
            if obj is not None:
                result: dict[str, ProviderConfig] = obj.__dict__["_providers"]
                return result
            return get_default_provider_registry()._providers  # type: ignore[return-value]

    _providers = _ProvidersDescriptor()  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Classmethods — backward-compatible public API.
    # Each delegates to the lazy default singleton with thread safety.
    # ------------------------------------------------------------------

    @classmethod
    def _get_default(cls) -> ProviderRegistry:
        return get_default_provider_registry()

    @classmethod
    def ensure_loaded(cls) -> None:
        """Ensure provider registrations are loaded into the registry."""
        from bioetl.composition.providers.loader import ensure_providers_loaded

        ensure_providers_loaded()

    @classmethod
    def register(cls, name: str, config: ProviderConfig) -> None:
        """Register a provider (re-registration overwrites, thread-safe)."""
        inst = cls._get_default()
        with inst._lock:
            register_provider_config(inst._providers, name, config)

    @classmethod
    def get(cls, name: str) -> ProviderConfig:
        """Return provider configuration; raises KeyError if unknown."""
        inst = cls._get_default()
        with inst._lock:
            return get_provider_config(inst._providers, name)

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check whether a provider is registered."""
        inst = cls._get_default()
        with inst._lock:
            return is_provider_registered(inst._providers, name)

    @classmethod
    def list_providers(cls) -> list[str]:
        """Return sorted list of registered provider names."""
        inst = cls._get_default()
        with inst._lock:
            return list_provider_names(inst._providers)

    @classmethod
    def has_data_source_creator(cls, name: str) -> bool:
        """Check whether a provider has a data_source_creator."""
        inst = cls._get_default()
        with inst._lock:
            if not is_provider_registered(inst._providers, name):
                return False
            return provider_has_data_source_creator(
                get_provider_config(inst._providers, name)
            )

    @classmethod
    def clear(cls) -> None:
        """Clear the registry (testing only, thread-safe)."""
        inst = cls._get_default()
        with inst._lock:
            inst._providers.clear()

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
        inst = cls._get_default()
        with inst._lock:
            config = get_provider_config(inst._providers, name)
        return create_provider_adapter(
            name=name, config=config,
            http_client=http_client, logger=logger, settings=settings, **kwargs,
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
        inst = cls._get_default()
        with inst._lock:
            config = get_provider_config(inst._providers, name)
        return create_provider_data_source(
            name=name, config=config, settings=settings,
            pipeline_config=pipeline_config, logger=logger,
            filter_config=filter_config, metrics=metrics,
            pipeline_name=pipeline_name,
        )

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
            return cls.create_data_source(
                name=name, settings=settings,
                pipeline_config=pipeline_config, logger=logger,
                filter_config=filter_config, metrics=metrics,
                pipeline_name=pipeline_name,
            )

        return creator

    # ------------------------------------------------------------------
    # Unified API (consistent with PipelineRegistry)
    # ------------------------------------------------------------------

    @classmethod
    def list_keys(cls) -> list[str]:
        """List all registered provider names (unified API)."""
        return cls.list_providers()

    @classmethod
    def contains(cls, key: str) -> bool:
        """Check if provider is registered (unified API)."""
        return cls.is_registered(key)


# ---------------------------------------------------------------------------
# Lazy default instance — avoids import-time side effects (DI-004).
# ---------------------------------------------------------------------------
_default_provider_registry: ProviderRegistry | None = None


def get_default_provider_registry() -> ProviderRegistry:
    """Get the default global provider registry instance.

    Created lazily on first access.  For tests, prefer ``create_provider_registry()``.
    """
    global _default_provider_registry
    if _default_provider_registry is None:
        _default_provider_registry = ProviderRegistry()
    return _default_provider_registry


def create_provider_registry() -> ProviderRegistry:
    """Create a new isolated provider registry instance."""
    return ProviderRegistry()
