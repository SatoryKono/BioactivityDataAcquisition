"""Leaf contracts and injected support for provider registration assembly."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.composition.providers._models import (
    DataSourceCreatorProtocol,
    HttpConfig,
    ProviderConfig,
)

if TYPE_CHECKING:
    from bioetl.composition.providers.provider_registry import ProviderRegistry
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
    from bioetl.domain.filtering import InputFilterConfig


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


class SupportAwareDataSourceCreatorProtocol(Protocol):
    """Protocol for data-source creators that accept injected assembly support."""

    def __call__(
        self,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
        *,
        assembly_support: ProviderAssemblySupport | None = None,
    ) -> DataSourcePort:
        """Create a fully configured data source with optional support injection."""
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


def resolve_provider_assembly_support(
    assembly_support: ProviderAssemblySupport | None,
    *,
    provider_registry: ProviderRegistry | None = None,
) -> ProviderAssemblySupport:
    """Return the injected support bundle or build the canonical default one."""
    if assembly_support is not None:
        return assembly_support

    return create_provider_assembly_support(provider_registry=provider_registry)


def bind_provider_data_source_creator(
    creator: SupportAwareDataSourceCreatorProtocol,
    *,
    assembly_support: ProviderAssemblySupport,
) -> DataSourceCreatorProtocol:
    """Bind the shared assembly support to a support-aware data-source creator."""
    return cast(
        DataSourceCreatorProtocol,
        partial(creator, assembly_support=assembly_support),
    )


def build_http_provider_config(
    *,
    adapter_class: type[DataSourcePort],
    rate: float,
    capacity: int,
    data_source_creator: SupportAwareDataSourceCreatorProtocol,
    assembly_support: ProviderAssemblySupport,
    rate_overrides: dict[str, float] | None = None,
    custom_creator: ProviderAdapterFactoryProtocol | None = None,
) -> ProviderConfig:
    """Build the common HTTP-oriented ProviderConfig shape for registration."""
    return ProviderConfig(
        adapter_class=adapter_class,
        http_config=HttpConfig(
            rate=rate,
            capacity=capacity,
            rate_overrides=rate_overrides or {},
        ),
        requires_http_client=True,
        requires_logger=True,
        custom_creator=custom_creator,
        data_source_creator=bind_provider_data_source_creator(
            data_source_creator,
            assembly_support=assembly_support,
        ),
    )
