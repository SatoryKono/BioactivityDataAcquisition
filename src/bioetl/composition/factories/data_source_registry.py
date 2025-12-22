"""Registry for data source creators.

Centralizes data source creation logic, eliminating duplication across pipeline factories.
Each provider registers a creator function that knows how to instantiate the appropriate
DataSourcePort implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Protocol

from bioetl.application.core.filtered_data_source import FilteredDataSource
from bioetl.composition.factories.data_sources import DataSourceFactory
from bioetl.composition.factories.http_client_factory import HttpClientFactory
from bioetl.infrastructure.adapters.input.csv_filter_reader import CsvFilterReader

if TYPE_CHECKING:
    from bioetl.domain.filter_config import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class DataSourceCreator(Protocol):
    """Protocol for data source creator functions."""

    def __call__(
        self,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        filter_config: InputFilterConfig | None = None,
    ) -> DataSourcePort:
        """Create a configured data source.

        Args:
            settings: Application settings
            pipeline_config: Pipeline configuration from YAML
            filter_config: Optional input filter configuration

        Returns:
            Configured DataSourcePort instance
        """
        ...


def _wrap_with_filter(
    data_source: DataSourcePort,
    filter_config: InputFilterConfig | None,
) -> DataSourcePort:
    """Wrap data source with FilteredDataSource if filter is enabled.

    Args:
        data_source: Base data source to wrap
        filter_config: Optional filter configuration

    Returns:
        Original data source or FilteredDataSource wrapper
    """
    if filter_config and filter_config.enabled:
        return FilteredDataSource(
            data_source=data_source,
            filter_reader=CsvFilterReader(),
            filter_config=filter_config,
        )
    return data_source


def create_chembl_data_source(
    settings: Settings,
    _pipeline_config: PipelineYamlConfig,
    filter_config: InputFilterConfig | None = None,
) -> DataSourcePort:
    """Create ChEMBL data source with optional CSV filtering."""
    http_client = HttpClientFactory.create_for_provider("chembl", settings)
    base_adapter = DataSourceFactory.create("chembl", http_client=http_client)
    return _wrap_with_filter(base_adapter, filter_config)


def create_pubchem_data_source(
    settings: Settings,
    _pipeline_config: PipelineYamlConfig,
    filter_config: InputFilterConfig | None = None,
) -> DataSourcePort:
    """Create PubChem data source."""
    # PubChem rate limit: 5 requests/second without API key
    data_source = DataSourceFactory.create(
        "pubchem",
        http_client=None,
        rate=5.0,
        strict_error_handling=settings.strict_error_handling,
    )
    return _wrap_with_filter(data_source, filter_config)


def create_uniprot_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    filter_config: InputFilterConfig | None = None,
) -> DataSourcePort:
    """Create UniProt data source."""
    http_client = HttpClientFactory.create_for_provider("uniprot", settings)

    data_source = DataSourceFactory.create(
        "uniprot",
        http_client=http_client,
        base_url=pipeline_config.source.api.base_url or "https://rest.uniprot.org",
        strict_error_handling=settings.strict_error_handling,
    )
    return _wrap_with_filter(data_source, filter_config)


def create_pubmed_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    filter_config: InputFilterConfig | None = None,
) -> DataSourcePort:
    """Create PubMed data source."""
    from bioetl.infrastructure.adapters.pubmed.pubmed_client import PubMedAdapter

    http_client = HttpClientFactory.create_for_provider("pubmed", settings)

    # Determine API key: config takes precedence over settings
    configured_api_key = pipeline_config.source.api_key
    settings_api_key = (
        settings.pubmed_api_key.get_secret_value() if settings.pubmed_api_key else None
    )
    api_key = configured_api_key or settings_api_key

    email = pipeline_config.source.email or settings.default_email

    data_source = PubMedAdapter(
        http_client=http_client,
        email=email,
        api_key=api_key,
    )
    return _wrap_with_filter(data_source, filter_config)


class DataSourceRegistry:
    """Registry for data source creators.

    Provides a centralized way to create data sources for different providers.
    Each provider registers a creator function that encapsulates provider-specific
    configuration logic.

    Example:
        >>> creator = DataSourceRegistry.get("chembl")
        >>> data_source = creator(settings, pipeline_config)
    """

    _creators: ClassVar[dict[str, DataSourceCreator]] = {
        "chembl": create_chembl_data_source,
        "pubchem": create_pubchem_data_source,
        "uniprot": create_uniprot_data_source,
        "pubmed": create_pubmed_data_source,
    }

    @classmethod
    def get(cls, provider: str) -> DataSourceCreator:
        """Get creator function for provider.

        Args:
            provider: Provider name (e.g., 'chembl', 'pubchem')

        Returns:
            Creator function for the provider

        Raises:
            KeyError: If provider is not registered
        """
        if provider not in cls._creators:
            available = ", ".join(cls._creators.keys())
            raise KeyError(f"Unknown provider: {provider}. Available: {available}")
        return cls._creators[provider]

    @classmethod
    def register(cls, provider: str, creator: DataSourceCreator) -> None:
        """Register a new data source creator.

        Args:
            provider: Provider name
            creator: Creator function
        """
        cls._creators[provider] = creator

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered providers."""
        return list(cls._creators.keys())
