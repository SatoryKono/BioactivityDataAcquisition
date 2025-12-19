"""Registry for data source creators.

Centralizes data source creation logic for all providers,
enabling declarative pipeline factory configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Protocol

from bioetl.composition.factories.http_client_factory import HttpClientFactory
from bioetl.infrastructure.factories.data_sources import DataSourceFactory

if TYPE_CHECKING:
    from bioetl.domain.filter_config import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class DataSourceCreator(Protocol):
    """Protocol for data source creation functions.

    Defines the contract for functions that create DataSourcePort instances.
    Each provider can have a custom creator that handles its specific
    configuration needs (HTTP clients, rate limits, API keys, etc.).
    """

    def __call__(
        self,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        filter_config: InputFilterConfig | None = None,
    ) -> DataSourcePort:
        """Create a data source for the specified provider.

        Args:
            settings: Application settings with credentials and environment config.
            pipeline_config: Pipeline-specific YAML configuration.
            filter_config: Optional input filter configuration for CSV filtering.

        Returns:
            Configured DataSourcePort instance.
        """
        ...


def _wrap_with_filter(
    data_source: DataSourcePort,
    filter_config: InputFilterConfig | None,
) -> DataSourcePort:
    """Wrap data source with FilteredDataSource if filter is enabled.

    Args:
        data_source: Base data source to potentially wrap.
        filter_config: Filter configuration (may be None or disabled).

    Returns:
        Original data source or FilteredDataSource wrapper.
    """
    if filter_config and filter_config.enabled:
        from bioetl.application.core.filtered_data_source import FilteredDataSource
        from bioetl.infrastructure.adapters.input.csv_filter_reader import (
            CsvFilterReader,
        )

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
    """Create ChEMBL data source with HTTP client and optional filtering.

    Args:
        settings: Application settings.
        _pipeline_config: Pipeline configuration (unused, kept for interface).
        filter_config: Optional filter configuration.

    Returns:
        ChEMBL DataSourcePort, optionally wrapped with filter.
    """
    http_client = HttpClientFactory.create_for_provider("chembl", settings)
    base_adapter = DataSourceFactory.create("chembl", http_client=http_client)
    return _wrap_with_filter(base_adapter, filter_config)


def create_pubchem_data_source(
    settings: Settings,
    _pipeline_config: PipelineYamlConfig,
    filter_config: InputFilterConfig | None = None,
) -> DataSourcePort:
    """Create PubChem data source with rate limiting.

    Args:
        settings: Application settings.
        _pipeline_config: Pipeline configuration (unused, kept for interface).
        filter_config: Optional filter configuration.

    Returns:
        PubChem DataSourcePort with 5 req/sec rate limit.
    """
    base_adapter = DataSourceFactory.create(
        "pubchem",
        http_client=None,
        rate=5.0,
        strict_error_handling=settings.strict_error_handling,
        filter_config=filter_config,
    )
    return _wrap_with_filter(base_adapter, filter_config)


def create_uniprot_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    filter_config: InputFilterConfig | None = None,
) -> DataSourcePort:
    """Create UniProt data source with HTTP client.

    Args:
        settings: Application settings.
        pipeline_config: Pipeline configuration.
        filter_config: Optional filter configuration.

    Returns:
        UniProt DataSourcePort.
    """
    source_config = pipeline_config.source.get("api", {})
    http_client = HttpClientFactory.create_for_provider("uniprot", settings)

    base_adapter = DataSourceFactory.create(
        "uniprot",
        http_client=http_client,
        base_url=source_config.get("base_url", "https://rest.uniprot.org"),
        strict_error_handling=settings.strict_error_handling,
    )
    return _wrap_with_filter(base_adapter, filter_config)


def create_pubmed_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    filter_config: InputFilterConfig | None = None,
) -> DataSourcePort:
    """Create PubMed data source with API key and email handling.

    Args:
        settings: Application settings.
        pipeline_config: Pipeline configuration.
        filter_config: Optional filter configuration.

    Returns:
        PubMed DataSourcePort.
    """
    from bioetl.infrastructure.adapters.pubmed.pubmed_client import PubMedAdapter

    http_client = HttpClientFactory.create_for_provider("pubmed", settings)

    # Resolve API key: pipeline config > settings
    configured_api_key = pipeline_config.source.api_key
    settings_api_key_value = (
        settings.pubmed_api_key.get_secret_value() if settings.pubmed_api_key else None
    )
    api_key_to_use = (
        configured_api_key if configured_api_key is not None else settings_api_key_value
    )

    # Resolve email: pipeline config > settings
    email_to_use = pipeline_config.source.email or settings.default_email

    base_adapter = PubMedAdapter(
        http_client=http_client,
        email=email_to_use,
        api_key=api_key_to_use,
    )
    return _wrap_with_filter(base_adapter, filter_config)


class DataSourceRegistry:
    """Registry for data source creators.

    Centralizes the mapping of provider names to their data source
    creation functions, enabling declarative pipeline configuration.

    Example:
        >>> creator = DataSourceRegistry.get("chembl")
        >>> data_source = creator(settings, config)
    """

    _creators: ClassVar[dict[str, DataSourceCreator]] = {
        "chembl": create_chembl_data_source,
        "pubchem": create_pubchem_data_source,
        "uniprot": create_uniprot_data_source,
        "pubmed": create_pubmed_data_source,
    }

    @classmethod
    def register(cls, provider: str, creator: DataSourceCreator) -> None:
        """Register a new data source creator.

        Args:
            provider: Provider name (e.g., 'chembl', 'pubchem').
            creator: Callable that creates DataSourcePort instances.
        """
        cls._creators[provider] = creator

    @classmethod
    def get(cls, provider: str) -> DataSourceCreator:
        """Get the data source creator for a provider.

        Args:
            provider: Provider name.

        Returns:
            DataSourceCreator callable.

        Raises:
            KeyError: If provider is not registered.
        """
        if provider not in cls._creators:
            available = list(cls._creators.keys())
            raise KeyError(
                f"Unknown provider: {provider}. Available: {available}"
            )
        return cls._creators[provider]

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered providers.

        Returns:
            List of provider names.
        """
        return list(cls._creators.keys())

    @classmethod
    def create(
        cls,
        provider: str,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        filter_config: InputFilterConfig | None = None,
    ) -> DataSourcePort:
        """Create a data source for the specified provider.

        Convenience method that combines get() and calling the creator.

        Args:
            provider: Provider name.
            settings: Application settings.
            pipeline_config: Pipeline configuration.
            filter_config: Optional filter configuration.

        Returns:
            Configured DataSourcePort.
        """
        creator = cls.get(provider)
        return creator(settings, pipeline_config, filter_config)
