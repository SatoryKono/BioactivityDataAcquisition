"""Provider registration ports migrated from composition (ADR-058)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort

    HttpConfig = object
    InputFilterConfig = object
    PipelineYamlConfig = object
    ProviderAssemblySupport = object
    ProviderConfig = object
    UnifiedHTTPClient = object


class SecretValueProviderProtocol(Protocol):
    """Minimal secret wrapper contract used by provider settings wiring."""

    def get_secret_value(self) -> str:
        """Return the resolved secret payload."""
        ...


class ProviderSettingsProtocol(Protocol):
    """Minimal settings surface required by provider registration helpers."""

    @property
    def gold_path(self) -> Path: ...

    @property
    def default_email(self) -> str | None: ...

    @property
    def strict_error_handling(self) -> bool: ...

    @property
    def pubmed_api_key(self) -> SecretValueProviderProtocol | None: ...

    @property
    def uniprot_api_key(self) -> SecretValueProviderProtocol | None: ...

    @property
    def openalex_api_key(self) -> SecretValueProviderProtocol | None: ...

    @property
    def semanticscholar_api_key(self) -> SecretValueProviderProtocol | None: ...


class AdapterCreatorProtocol(Protocol):
    """Protocol for typed composition-owned provider adapter creators."""

    def __call__(
        self,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: ProviderSettingsProtocol | None = None,
        **kwargs: object,
    ) -> DataSourcePort: ...


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


class ProviderRegistrarProtocol(Protocol):
    """Minimal registry contract for provider registration assembly."""

    def register(self, name: str, config: ProviderConfig) -> None: ...

    def is_registered(self, name: str) -> bool: ...

    def list_providers(self) -> list[str]: ...

    def clear(self) -> None: ...


class ProviderDataSourceAccessProtocol(ProviderRegistrarProtocol, Protocol):
    """Registry contract required by datasource and HTTP-client factories."""

    def get_http_config(self, name: str) -> HttpConfig | None: ...

    def create_adapter(
        self,
        name: str,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: ProviderSettingsProtocol | None = None,
        **kwargs: object,
    ) -> DataSourcePort: ...

    def create_data_source(
        self,
        name: str,
        settings: ProviderSettingsProtocol,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort: ...

    def build_data_source_creator(self, name: str) -> DataSourceCreatorProtocol: ...
