"""Explicit provider registration for Composition layer.

Loads config from configs/sources/*.yaml. HttpConfig serves as fallback.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from bioetl.application.core.document_term_data_source import DocumentTermDataSource
from bioetl.application.core.filtered_data_source import FilteredDataSource
from bioetl.application.core.idmapping_data_source import IDMappingDataSource
from bioetl.composition.providers.provider_registry import (
    HttpConfig,
    ProviderConfig,
    ProviderRegistry,
)
from bioetl.domain.resilience import AdapterConfig

# Import adapter classes from Infrastructure (allowed direction)
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.crossref.client import (
    CrossRefAdapter,
    _create_crossref_adapter,
)
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.adapters.input.csv_filter_reader import CsvFilterReader
from bioetl.infrastructure.adapters.openalex.client import (
    OpenAlexAdapter,
    _create_openalex_adapter,
)
from bioetl.infrastructure.adapters.pubchem.client import PubChemAdapter
from bioetl.infrastructure.adapters.pubmed.pubmed_client import (
    PubMedAdapter,
    _create_pubmed_adapter,
)
from bioetl.infrastructure.adapters.semanticscholar.adapter import (
    SemanticScholarAdapter,
)
from bioetl.infrastructure.adapters.uniprot.client import UniProtAdapter
from bioetl.infrastructure.adapters.uniprot.idmapping_client import (
    UniProtIDMappingClient,
)
from bioetl.infrastructure.config import load_source_config

if TYPE_CHECKING:
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
    from bioetl.infrastructure.schemas.source_config import SourceYamlConfig

_logger = logging.getLogger(__name__)


def _get_factories() -> tuple[Any, Any]:
    """Lazy import factories to avoid circular imports."""
    from bioetl.composition.factories.data_source_factory import DataSourceFactory
    from bioetl.composition.factories.http_client_factory import HttpClientFactory

    return DataSourceFactory, HttpClientFactory


def _get_source_config(provider: str) -> SourceYamlConfig | None:
    """Load config from configs/sources/{provider}.yaml or return None."""
    try:
        return load_source_config(provider)
    except ValueError:
        _logger.debug("Source config not found for %s, using defaults", provider)
        return None


def _get_batch_size_from_config(provider: str, default: int = 100) -> int:
    """Get batch size from source config or return default."""
    source_config = _get_source_config(provider)
    return source_config.batch_size if source_config else default


def _get_rate_limit_from_config(provider: str) -> tuple[float, int]:
    """Get (rate, capacity) from source config or defaults (5.0, 10)."""
    source_config = _get_source_config(provider)
    if source_config:
        return (
            source_config.rate_limit.requests_per_second,
            source_config.rate_limit.burst,
        )
    return 5.0, 10


def _get_circuit_breaker_from_config(provider: str) -> tuple[int, int]:
    """Get (failure_threshold, recovery_timeout) from config or defaults (5, 300)."""
    source_config = _get_source_config(provider)
    if source_config:
        return (
            source_config.circuit_breaker.failure_threshold,
            source_config.circuit_breaker.recovery_timeout,
        )
    return 5, 300


def _get_adapter_config(provider: str, default_page_size: int = 1000) -> AdapterConfig:
    """Get AdapterConfig from source YAML config.

    This is the single source of truth for adapter parameters (RULES.md §12.1.2).
    Loads from configs/sources/{provider}.yaml and converts to domain dataclass.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem')
        default_page_size: Default page size if not specified in config

    Returns:
        AdapterConfig: Immutable adapter configuration

    Raises:
        ValueError: If source config is missing and fail_fast is True
    """
    source_config = _get_source_config(provider)
    if source_config is not None:
        return source_config.to_adapter_config(default_page_size=default_page_size)

    # Fallback to domain defaults
    _logger.warning(
        "Source config not found for %s, using AdapterConfig defaults. "
        "Create configs/sources/%s.yaml to configure adapter parameters.",
        provider,
        provider,
    )
    return AdapterConfig(page_size=default_page_size)


def _wrap_with_filter(
    data_source: DataSourcePort,
    filter_config: InputFilterConfig | None,
    logger: LoggerPort | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Wrap data source with FilteredDataSource if filter is enabled."""
    if filter_config and filter_config.enabled:
        return FilteredDataSource(
            data_source=data_source,
            filter_reader=CsvFilterReader(logger=logger),
            filter_config=filter_config,
            metrics=metrics,
            pipeline_name=pipeline_name,
            logger=logger,
        )
    return data_source


def _create_chembl_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create ChEMBL data source with optional CSV filtering.

    Configuration is loaded from configs/sources/chembl.yaml via AdapterConfig.
    This ensures YAML is the single source of truth (RULES.md §12.1.2).

    For document_term entity type, wraps the adapter with DocumentTermDataSource
    to extract terms from document records (derived entity pattern).
    """
    DataSourceFactory, HttpClientFactory = _get_factories()
    http_client = HttpClientFactory.create_for_provider("chembl", settings)

    # Load adapter configuration from YAML (single source of truth)
    adapter_config = _get_adapter_config("chembl", default_page_size=1000)

    base_adapter = DataSourceFactory.create(
        "chembl",
        http_client=http_client,
        logger=logger,
        adapter_config=adapter_config,
        metrics=metrics,
    )

    # Wrap with DocumentTermDataSource for derived entity extraction
    # document_term is extracted from document records (1:M relationship)
    if pipeline_config.entity_type == "document_term":
        base_adapter = DocumentTermDataSource(base_adapter)

    return _wrap_with_filter(
        base_adapter, filter_config, logger, metrics, pipeline_name
    )


def _create_pubchem_adapter(
    http_client: UnifiedHTTPClient | None = None,
    logger: LoggerPort | None = None,
    settings: Settings | None = None,
    **kwargs: Any,
) -> DataSourcePort:
    """Create PubChem adapter with all dependencies injected from Composition Root."""
    if logger is None:
        raise ValueError("PubChem adapter requires logger")

    rate, capacity = _get_rate_limit_from_config("pubchem")
    cb_threshold, cb_timeout = _get_circuit_breaker_from_config("pubchem")

    rate = kwargs.pop("rate", rate)
    capacity = kwargs.pop("capacity", capacity)
    cb_threshold = kwargs.pop("circuit_breaker_threshold", cb_threshold)
    cb_timeout = kwargs.pop("circuit_breaker_timeout", cb_timeout)
    max_workers = kwargs.pop("max_workers", 4)
    strict_error_handling = kwargs.pop("strict_error_handling", False)
    metrics = kwargs.pop("metrics", None)

    return PubChemAdapter(
        logger=logger,
        rate_limiter=TokenBucket(rate=rate, capacity=capacity, provider="pubchem"),
        circuit_breaker=CircuitBreaker(
            provider="pubchem",
            failure_threshold=cb_threshold,
            recovery_timeout=cb_timeout,
            metrics=metrics,
        ),
        thread_pool=ThreadPoolExecutor(max_workers=max_workers),
        strict_error_handling=strict_error_handling,
    )


def _create_pubchem_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create PubChem data source with optional CSV filtering."""
    data_source = _create_pubchem_adapter(
        logger=logger,
        settings=settings,
        strict_error_handling=settings.strict_error_handling,
        metrics=metrics,
    )
    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _create_uniprot_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create UniProt data source with optional CSV filtering."""
    DataSourceFactory, HttpClientFactory = _get_factories()
    http_client = HttpClientFactory.create_for_provider("uniprot", settings)
    data_source = DataSourceFactory.create(
        "uniprot",
        http_client=http_client,
        logger=logger,
        base_url=pipeline_config.source.api.base_url or "https://rest.uniprot.org",
        strict_error_handling=settings.strict_error_handling,
    )
    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _create_pubmed_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create PubMed data source with optional CSV filtering."""
    _, HttpClientFactory = _get_factories()
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
        logger=logger,
        email=email,
        api_key=api_key,
    )
    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _create_crossref_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create CrossRef data source with optional CSV filtering.

    CrossRef requires mailto for polite pool access (50 req/sec vs 1 req/sec).
    Email is obtained from pipeline config or settings.default_email.

    Args:
        settings: Application settings.
        pipeline_config: Pipeline configuration from YAML.
        logger: LoggerPort for structured logging.
        filter_config: Optional filter configuration for CSV-based DOI filtering.
        metrics: Optional MetricsPort for recording adapter metrics.
        pipeline_name: Pipeline name for metrics labels.

    Returns:
        Configured DataSourcePort with optional filtering wrapper.

    Raises:
        ValueError: If mailto is not configured in settings or pipeline config.

    """
    _, HttpClientFactory = _get_factories()
    http_client = HttpClientFactory.create_for_provider("crossref", settings)

    # Get mailto from pipeline config or settings
    mailto = pipeline_config.source.email or settings.default_email
    batch_size = _get_batch_size_from_config("crossref", default=50)

    data_source = _create_crossref_adapter(
        http_client=http_client,
        logger=logger,
        settings=settings,
        mailto=mailto,
        batch_size=batch_size,
        metrics=metrics,
    )
    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _create_openalex_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create OpenAlex data source with optional CSV filtering.

    OpenAlex requires mailto for polite pool access (10 req/sec).
    Email is obtained from pipeline config or settings.default_email.

    Args:
        settings: Application settings.
        pipeline_config: Pipeline configuration from YAML.
        logger: LoggerPort for structured logging.
        filter_config: Optional filter configuration for CSV-based DOI filtering.
        metrics: Optional MetricsPort for recording adapter metrics.
        pipeline_name: Pipeline name for metrics labels.

    Returns:
        Configured DataSourcePort with optional filtering wrapper.

    Raises:
        ValueError: If mailto is not configured in settings or pipeline config.

    """
    _, HttpClientFactory = _get_factories()
    http_client = HttpClientFactory.create_for_provider("openalex", settings)

    # Get mailto from pipeline config or settings
    mailto = pipeline_config.source.email or settings.default_email
    batch_size = _get_batch_size_from_config("openalex", default=50)

    data_source = _create_openalex_adapter(
        http_client=http_client,
        logger=logger,
        settings=settings,
        mailto=mailto,
        batch_size=batch_size,
        metrics=metrics,
    )
    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _create_semanticscholar_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create Semantic Scholar data source with optional CSV filtering.

    Semantic Scholar requires API key for stable rate limits (1 req/sec).
    API key is obtained from settings.semanticscholar_api_key.

    Args:
        settings: Application settings.
        pipeline_config: Pipeline configuration from YAML.
        logger: LoggerPort for structured logging.
        filter_config: Optional filter configuration for CSV-based DOI filtering.
        metrics: Optional MetricsPort for recording adapter metrics.
        pipeline_name: Pipeline name for metrics labels.

    Returns:
        Configured DataSourcePort with optional filtering wrapper.

    """
    _, HttpClientFactory = _get_factories()
    http_client = HttpClientFactory.create_for_provider("semanticscholar", settings)

    # Get API key from settings (configured via BIOETL_SEMANTICSCHOLAR_API_KEY env var)
    api_key = (
        settings.semanticscholar_api_key.get_secret_value()
        if settings.semanticscholar_api_key
        else ""
    )
    if not api_key:
        logger.warning(
            "semanticscholar_no_api_key",
            message="No API key provided. Rate limits will be shared with other users.",
        )

    batch_size = _get_batch_size_from_config("semanticscholar", default=100)

    data_source = SemanticScholarAdapter(
        http_client=http_client,
        logger=logger,
        api_key=api_key,
        batch_size=batch_size,
        metrics=metrics,
    )

    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _create_uniprot_idmapping_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create UniProt ID Mapping data source.

    Creates an IDMappingDataSource that:
    1. Reads ChEMBL target IDs from input CSV file
    2. Calls UniProt ID Mapping API to map to UniProt accessions
    3. Yields records with mapping results

    Args:
        settings: Application settings.
        pipeline_config: Pipeline configuration from YAML.
        logger: LoggerPort for structured logging.
        filter_config: Unused (filtering happens via input_path CSV).
        metrics: Optional MetricsPort for recording adapter metrics.
        pipeline_name: Pipeline name for metrics labels.

    Returns:
        Configured IDMappingDataSource instance.
    """
    from pathlib import Path

    # Ignore filter_config - the input file IS the data source
    _ = filter_config

    _, HttpClientFactory = _get_factories()

    # Create HTTP client for ID Mapping API
    http_client = HttpClientFactory.create_for_provider("uniprot", settings)

    # Create ID Mapping client
    base_url = "https://rest.uniprot.org"
    if pipeline_config.source.api and pipeline_config.source.api.base_url:
        base_url = pipeline_config.source.api.base_url
    idmapping_client = UniProtIDMappingClient(
        http_client=http_client,
        logger=logger,
        metrics=metrics,
        base_url=base_url,
    )

    # Get input path from pipeline config
    input_path_str = (
        pipeline_config.source.input_path
        if hasattr(pipeline_config.source, "input_path")
        else "data/input/target.csv"
    )
    input_path = Path(input_path_str)

    # Get database names from API config
    from_db = "ChEMBL"
    to_db = "UniProtKB"
    if pipeline_config.source.api:
        from_db = getattr(pipeline_config.source.api, "from_db", from_db)
        to_db = getattr(pipeline_config.source.api, "to_db", to_db)

    return IDMappingDataSource(
        idmapping_client=idmapping_client,
        input_path=input_path,
        logger=logger,
        from_db=from_db,
        to_db=to_db,
    )


# =============================================================================
# Provider registration
# =============================================================================


def register_all_providers() -> None:
    """Explicitly register all data source providers.

    This function MUST be called from bootstrap before using ProviderRegistry.
    Idempotent - safe to call multiple times.

    Configuration Priority:
    1. configs/sources/{provider}.yaml - PRIMARY (rate limits, circuit breaker, batch_size)
    2. HttpConfig in ProviderConfig - FALLBACK only

    Provider configurations are now loaded from YAML files:
    - ChEMBL: configs/sources/chembl.yaml
    - PubChem: configs/sources/pubchem.yaml
    - UniProt: configs/sources/uniprot.yaml
    - PubMed: configs/sources/pubmed.yaml
    - CrossRef: configs/sources/crossref.yaml
    - OpenAlex: configs/sources/openalex.yaml
    - Semantic Scholar: configs/sources/semanticscholar.yaml

    Each provider includes a data_source_creator for unified registry access.
    """
    # Load rate limits from source configs (with fallback defaults)
    chembl_rate, chembl_capacity = _get_rate_limit_from_config("chembl")
    pubchem_rate, pubchem_capacity = _get_rate_limit_from_config("pubchem")
    uniprot_rate, uniprot_capacity = _get_rate_limit_from_config("uniprot")
    pubmed_rate, pubmed_capacity = _get_rate_limit_from_config("pubmed")
    crossref_rate, crossref_capacity = _get_rate_limit_from_config("crossref")

    # ChEMBL - async HTTP adapter
    if not ProviderRegistry.is_registered("chembl"):
        ProviderRegistry.register(
            "chembl",
            ProviderConfig(
                adapter_class=ChemblAdapter,
                http_config=HttpConfig(
                    rate=chembl_rate,
                    capacity=chembl_capacity,
                ),
                requires_http_client=True,
                requires_logger=True,
                data_source_creator=_create_chembl_data_source,
            ),
        )

    # PubChem - sync adapter with DI-compliant custom creator
    # Dependencies (TokenBucket, CircuitBreaker, ThreadPoolExecutor) are created
    # in _create_pubchem_adapter following Composition Root pattern
    if not ProviderRegistry.is_registered("pubchem"):
        ProviderRegistry.register(
            "pubchem",
            ProviderConfig(
                adapter_class=PubChemAdapter,
                http_config=HttpConfig(
                    rate=pubchem_rate,
                    capacity=pubchem_capacity,
                ),
                requires_http_client=False,
                requires_logger=True,
                custom_creator=_create_pubchem_adapter,
                data_source_creator=_create_pubchem_data_source,
            ),
        )

    # UniProt - async HTTP adapter with conditional rate override
    if not ProviderRegistry.is_registered("uniprot"):
        ProviderRegistry.register(
            "uniprot",
            ProviderConfig(
                adapter_class=UniProtAdapter,
                http_config=HttpConfig(
                    rate=uniprot_rate,
                    capacity=uniprot_capacity,
                    rate_overrides={"uniprot_api_key": 100.0},
                ),
                requires_http_client=True,
                requires_logger=True,
                data_source_creator=_create_uniprot_data_source,
            ),
        )

    # PubMed - async HTTP adapter with custom creator for email/API key handling
    if not ProviderRegistry.is_registered("pubmed"):
        ProviderRegistry.register(
            "pubmed",
            ProviderConfig(
                adapter_class=PubMedAdapter,
                http_config=HttpConfig(
                    rate=pubmed_rate,
                    capacity=pubmed_capacity,
                    rate_overrides={"pubmed_api_key": 10.0},
                ),
                requires_http_client=True,
                requires_logger=True,
                custom_creator=_create_pubmed_adapter,
                data_source_creator=_create_pubmed_data_source,
            ),
        )

    # CrossRef - async HTTP adapter for DOI resolution and publication metadata
    # Requires mailto for polite pool access (50 req/sec vs 1 req/sec without)
    if not ProviderRegistry.is_registered("crossref"):
        ProviderRegistry.register(
            "crossref",
            ProviderConfig(
                adapter_class=CrossRefAdapter,
                http_config=HttpConfig(
                    rate=crossref_rate,
                    capacity=crossref_capacity,
                ),
                requires_http_client=True,
                requires_logger=True,
                custom_creator=_create_crossref_adapter,
                data_source_creator=_create_crossref_data_source,
            ),
        )

    # OpenAlex - async HTTP adapter for open scholarly metadata
    # Requires mailto for polite pool access (10 req/sec)
    # Supports batch DOI resolution with title fallback
    openalex_rate, openalex_capacity = _get_rate_limit_from_config("openalex")
    if not ProviderRegistry.is_registered("openalex"):
        ProviderRegistry.register(
            "openalex",
            ProviderConfig(
                adapter_class=OpenAlexAdapter,
                http_config=HttpConfig(
                    rate=openalex_rate,
                    capacity=openalex_capacity,
                ),
                requires_http_client=True,
                requires_logger=True,
                custom_creator=_create_openalex_adapter,
                data_source_creator=_create_openalex_data_source,
            ),
        )

    # Semantic Scholar - async HTTP adapter for DOI resolution with title fallback
    # API key recommended for stable rate limits (1 req/sec guaranteed)
    s2_rate, s2_capacity = _get_rate_limit_from_config("semanticscholar")
    if not ProviderRegistry.is_registered("semanticscholar"):
        ProviderRegistry.register(
            "semanticscholar",
            ProviderConfig(
                adapter_class=SemanticScholarAdapter,
                http_config=HttpConfig(
                    rate=s2_rate,
                    capacity=s2_capacity,
                ),
                requires_http_client=True,
                requires_logger=True,
                data_source_creator=_create_semanticscholar_data_source,
            ),
        )

    # UniProt ID Mapping - maps ChEMBL target IDs to UniProt accessions
    # Uses UniProt ID Mapping REST API (job-based async)
    # Input comes from CSV file, not external API filtering
    # Note: IDMappingDataSource is a lightweight wrapper, actual API client is
    # UniProtIDMappingClient created in the data_source_creator
    uniprot_idmapping_rate, uniprot_idmapping_capacity = _get_rate_limit_from_config(
        "uniprot"
    )
    if not ProviderRegistry.is_registered("uniprot_idmapping"):
        ProviderRegistry.register(
            "uniprot_idmapping",
            ProviderConfig(
                adapter_class=IDMappingDataSource,
                http_config=HttpConfig(
                    rate=uniprot_idmapping_rate,
                    capacity=uniprot_idmapping_capacity,
                ),
                requires_http_client=True,
                requires_logger=True,
                data_source_creator=_create_uniprot_idmapping_data_source,
            ),
        )
