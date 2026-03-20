"""Leaf contracts and injected support for provider registration assembly."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Protocol

from bioetl.composition.providers._models import ProviderConfig

if TYPE_CHECKING:
    from bioetl.composition.providers.provider_registry import ProviderRegistry
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings


class ProviderRegistrarProtocol(Protocol):
    """Minimal registry contract for provider registration assembly."""

    def register(self, name: str, config: ProviderConfig) -> None:
        """Register a provider config."""
        ...

    def is_registered(self, name: str) -> bool:
        """Return whether the provider is already registered."""
        ...

    def list_providers(self) -> list[str]:
        """List registered providers."""
        ...

    def clear(self) -> None:
        """Clear all registered providers."""
        ...


class ProviderHttpClientFactoryProtocol(Protocol):
    """Callable contract for provider HTTP client construction."""

    def __call__(
        self,
        provider: str,
        settings: Settings | None = None,
        *,
        metrics: MetricsPort | None = None,
        logger: LoggerPort | None = None,
    ) -> UnifiedHTTPClient:
        """Create a provider-scoped HTTP client."""
        ...


class ProviderAdapterFactoryProtocol(Protocol):
    """Callable contract for provider adapter construction."""

    def __call__(
        self,
        provider: str,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: Settings | None = None,
        **kwargs: object,
    ) -> DataSourcePort:
        """Create a provider adapter via composition-owned wiring."""
        ...


@dataclass(frozen=True)
class ProviderAssemblySupport:
    """Injected factory callbacks for provider registration definitions."""

    create_http_client: ProviderHttpClientFactoryProtocol
    create_adapter: ProviderAdapterFactoryProtocol


def _create_http_client_for_provider(
    provider: str,
    settings: Settings | None = None,
    *,
    metrics: MetricsPort | None = None,
    logger: LoggerPort | None = None,
    provider_registry: ProviderRegistry | None = None,
) -> UnifiedHTTPClient:
    """Resolve the canonical HTTP client factory lazily at the composition edge."""
    from bioetl.composition.factories.datasource.http_client import HttpClientFactory

    return HttpClientFactory.create_for_provider(
        provider,
        settings,
        metrics=metrics,
        logger=logger,
        provider_registry=provider_registry,
    )


def _create_adapter_for_provider(
    provider: str,
    http_client: UnifiedHTTPClient | None = None,
    logger: LoggerPort | None = None,
    settings: Settings | None = None,
    *,
    provider_registry: ProviderRegistry | None = None,
    **kwargs: object,
) -> DataSourcePort:
    """Resolve the canonical adapter factory lazily at the composition edge."""
    from bioetl.composition.factories.datasource.data_source_factory import (
        DataSourceFactory,
    )

    return DataSourceFactory.create(
        provider,
        http_client=http_client,
        logger=logger,
        settings=settings,
        provider_registry=provider_registry,
        **kwargs,
    )


def create_provider_assembly_support(
    *,
    provider_registry: ProviderRegistry | None = None,
) -> ProviderAssemblySupport:
    """Build the default injected support bundle for provider registration."""
    return ProviderAssemblySupport(
        create_http_client=partial(
            _create_http_client_for_provider,
            provider_registry=provider_registry,
        ),
        create_adapter=partial(
            _create_adapter_for_provider,
            provider_registry=provider_registry,
        ),
    )
