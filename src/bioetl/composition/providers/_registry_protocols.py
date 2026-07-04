"""Neutral protocol contracts shared by provider-registry helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.composition.providers._models import (
        DataSourceCreatorProtocol,
        HttpConfig,
        ProviderConfig,
        ProviderSettingsProtocol,
    )
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


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


class ProviderDataSourceAccessProtocol(ProviderRegistrarProtocol, Protocol):
    """Registry contract required by datasource and HTTP-client factories."""

    def get_http_config(self, name: str) -> HttpConfig | None:
        """Return the HTTP configuration for a provider, or None."""
        ...

    def create_adapter(
        self,
        name: str,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: ProviderSettingsProtocol | None = None,
        **kwargs: object,
    ) -> DataSourcePort:
        """Create a provider adapter instance using registry metadata."""
        ...

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
        """Create a fully configured provider data source."""
        ...

    def build_data_source_creator(self, name: str) -> DataSourceCreatorProtocol:
        """Return a provider-bound data-source creator closure."""
        ...
