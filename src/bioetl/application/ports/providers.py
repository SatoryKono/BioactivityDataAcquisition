"""Provider registration ports migrated from composition (ADR-058)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort

    InputFilterConfig = object
    PipelineYamlConfig = object
    ProviderAssemblySupport = object
    ProviderConfig = object
    UnifiedHTTPClient = object


@dataclass(frozen=True)
class HttpConfig:
    """HTTP client configuration returned by provider registries."""

    rate: float = 5.0
    capacity: int = 10


@runtime_checkable
class SecretValueProviderProtocol(Protocol):
    """Minimal secret wrapper contract used by provider settings wiring."""

    def get_secret_value(self) -> str:
        """Return the resolved secret payload."""
        ...


@runtime_checkable
class ProviderSettingsProtocol(Protocol):
    """Minimal settings surface required by provider registration helpers."""

    @property
    def gold_path(self) -> Path:
        """Gold-layer output path from provider settings."""
        ...

    @property
    def default_email(self) -> str | None:
        """Optional default contact email for provider HTTP clients."""
        ...

    @property
    def strict_error_handling(self) -> bool:
        """Whether provider failures must fail closed."""
        ...

    @property
    def pubmed_api_key(self) -> SecretValueProviderProtocol | None:
        """Optional PubMed API key wrapper."""
        ...

    @property
    def uniprot_api_key(self) -> SecretValueProviderProtocol | None:
        """Optional UniProt API key wrapper."""
        ...

    @property
    def openalex_api_key(self) -> SecretValueProviderProtocol | None:
        """Optional OpenAlex API key wrapper."""
        ...

    @property
    def semanticscholar_api_key(self) -> SecretValueProviderProtocol | None:
        """Optional Semantic Scholar API key wrapper."""
        ...


@runtime_checkable
class AdapterCreatorProtocol(Protocol):
    """Protocol for typed composition-owned provider adapter creators."""

    def __call__(
        self,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: ProviderSettingsProtocol | None = None,
        **kwargs: object,
    ) -> DataSourcePort: ...


@runtime_checkable
class DataSourceCreatorProtocol(Protocol):
    """Protocol for composition-side data source creator callables."""

    def __call__(
        self,
        settings: ProviderSettingsProtocol,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort: ...


@runtime_checkable
class ProviderHttpClientFactoryProtocol(Protocol):
    """Callable contract for provider HTTP client construction."""

    def __call__(
        self,
        provider: str,
        settings: ProviderSettingsProtocol | None = None,
        *,
        metrics: MetricsPort | None = None,
        logger: LoggerPort | None = None,
    ) -> UnifiedHTTPClient: ...


@runtime_checkable
class ProviderAdapterFactoryProtocol(Protocol):
    """Callable contract for provider adapter construction."""

    def __call__(
        self,
        provider: str,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: ProviderSettingsProtocol | None = None,
        **kwargs: object,
    ) -> DataSourcePort: ...


@runtime_checkable
class SupportAwareDataSourceCreatorProtocol(Protocol):
    """Protocol for data-source creators that accept injected assembly support."""

    def __call__(
        self,
        settings: ProviderSettingsProtocol,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
        *,
        assembly_support: ProviderAssemblySupport | None = None,
    ) -> DataSourcePort: ...


@runtime_checkable
class ProviderRegistrarProtocol(Protocol):
    """Minimal registry contract for provider registration assembly."""

    def register(self, name: str, config: ProviderConfig) -> None:
        """Register a named provider configuration."""
        ...

    def is_registered(self, name: str) -> bool:
        """Return whether a provider name is registered."""
        ...

    def list_providers(self) -> list[str]:
        """List registered provider names."""
        ...

    def clear(self) -> None:
        """Remove all registered providers."""
        ...


@runtime_checkable
class ProviderDataSourceAccessProtocol(ProviderRegistrarProtocol, Protocol):
    """Registry contract required by datasource and HTTP-client factories."""

    def get_http_config(self, name: str) -> HttpConfig | None:
        """Return HTTP client config for a provider, if registered."""
        ...

    def create_adapter(
        self,
        name: str,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: ProviderSettingsProtocol | None = None,
        **kwargs: object,
    ) -> DataSourcePort:
        """Create a provider adapter for the given name."""
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
        """Create a data source for the given provider name."""
        ...

    def build_data_source_creator(self, name: str) -> DataSourceCreatorProtocol:
        """Build a data-source creator bound to one provider."""
        ...
