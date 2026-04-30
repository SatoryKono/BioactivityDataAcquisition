"""Internal provider registry models and creator contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "AdapterCreator",
    "DataSourceCreatorProtocol",
    "HttpConfig",
    "ProviderConfig",
    "ProviderSettingsProtocol",
]


AdapterCreator = Callable[..., "DataSourcePort"]


class SecretValueProviderProtocol(Protocol):
    """Minimal secret wrapper contract used by provider settings wiring."""

    def get_secret_value(self) -> str:
        """Return the resolved secret payload."""
        ...


class ProviderSettingsProtocol(Protocol):
    """Minimal settings surface required by provider registration helpers."""

    @property
    def default_email(self) -> str | None:
        """Return the default contact email used by provider clients."""
        ...

    @property
    def strict_error_handling(self) -> bool:
        """Return whether provider adapters should fail fast on recoverable errors."""
        ...

    @property
    def pubmed_api_key(self) -> SecretValueProviderProtocol | None:
        """Return the configured PubMed API key wrapper when available."""
        ...

    @property
    def uniprot_api_key(self) -> SecretValueProviderProtocol | None:
        """Return the configured UniProt API key wrapper when available."""
        ...

    @property
    def openalex_api_key(self) -> SecretValueProviderProtocol | None:
        """Return the configured OpenAlex API key wrapper when available."""
        ...

    @property
    def semanticscholar_api_key(self) -> SecretValueProviderProtocol | None:
        """Return the configured Semantic Scholar API key wrapper when available."""
        ...


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
    ) -> DataSourcePort:
        """Create a fully configured data source."""
        ...


@dataclass(frozen=True)
class HttpConfig:
    """HTTP client configuration for a provider."""

    rate: float = 5.0
    capacity: int = 10
    rate_overrides: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderConfig:
    """Complete provider configuration used by the composition registry."""

    adapter_class: type[DataSourcePort]
    http_config: HttpConfig | None = None
    requires_http_client: bool = True
    requires_logger: bool = True
    default_kwargs: dict[str, object] = field(default_factory=dict)
    custom_creator: AdapterCreator | None = None
    data_source_creator: DataSourceCreatorProtocol | None = None
