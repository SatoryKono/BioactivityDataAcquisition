"""Explicit provider registration.

Centralizes all provider registrations in the Composition layer.
This ensures Infrastructure layer does NOT import from Composition.

This module follows the Hexagonal Architecture import matrix:
- Composition CAN import from Infrastructure (allowed)
- Infrastructure MUST NOT import from Composition (forbidden)

After registry unification, this module also contains data source creator
functions that were previously in DataSourceRegistry.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from bioetl.application.core.filtered_data_source import FilteredDataSource
from bioetl.composition.providers.provider_registry import (
    HttpConfig,
    ProviderConfig,
    ProviderRegistry,
)

# Import adapter classes from Infrastructure (allowed direction)
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.adapters.input.csv_filter_reader import CsvFilterReader
from bioetl.infrastructure.adapters.pubchem.client import PubChemAdapter
from bioetl.infrastructure.adapters.pubmed.pubmed_client import (
    PubMedAdapter,
    _create_pubmed_adapter,
)
from bioetl.infrastructure.adapters.uniprot.client import UniProtAdapter

if TYPE_CHECKING:
    from bioetl.domain.filter_config import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _get_factories() -> tuple[Any, Any]:
    """Lazy import factories to avoid circular imports.

    Returns:
        Tuple of (DataSourceFactory, HttpClientFactory)

    Note:
        Returns Any types to avoid TYPE_CHECKING circular imports with factories.
        The factory classes have create() and create_for_provider() methods.
    """
    from bioetl.composition.factories.data_source_factory import DataSourceFactory
    from bioetl.composition.factories.http_client_factory import HttpClientFactory

    return DataSourceFactory, HttpClientFactory


# =============================================================================
# Helper functions for data source creation
# =============================================================================


def _wrap_with_filter(
    data_source: DataSourcePort,
    filter_config: InputFilterConfig | None,
    logger: LoggerPort | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Wrap data source with FilteredDataSource if filter is enabled.

    Args:
        data_source: Base data source to wrap
        filter_config: Optional filter configuration
        logger: Optional LoggerPort for CsvFilterReader logging
        metrics: Optional metrics port for recording filter statistics
        pipeline_name: Pipeline name for metrics labels

    Returns:
        Original data source or FilteredDataSource wrapper
    """
    if filter_config and filter_config.enabled:
        return FilteredDataSource(
            data_source=data_source,
            filter_reader=CsvFilterReader(logger=logger),
            filter_config=filter_config,
            metrics=metrics,
            pipeline_name=pipeline_name,
        )
    return data_source


# =============================================================================
# Data source creator functions (unified from DataSourceRegistry)
# =============================================================================


def _create_chembl_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create ChEMBL data source with optional CSV filtering."""
    DataSourceFactory, HttpClientFactory = _get_factories()
    http_client = HttpClientFactory.create_for_provider("chembl", settings)
    base_adapter = DataSourceFactory.create(
        "chembl", http_client=http_client, logger=logger
    )
    return _wrap_with_filter(
        base_adapter, filter_config, logger, metrics, pipeline_name
    )


def _create_pubchem_adapter(
    http_client: UnifiedHTTPClient | None = None,
    logger: LoggerPort | None = None,
    settings: Settings | None = None,
    **kwargs: Any,
) -> DataSourcePort:
    """Create PubChem adapter with all dependencies injected.

    This is the custom_creator for PubChem that creates all dependencies
    in the Composition Root before creating the adapter.

    Args:
        http_client: Not used for PubChem (uses pubchempy).
        logger: LoggerPort instance for structured logging.
        settings: Application settings.
        **kwargs: Additional keyword arguments (e.g., strict_error_handling).

    Returns:
        Configured PubChemAdapter instance.

    Raises:
        ValueError: If logger is not provided.
    """
    if logger is None:
        raise ValueError(
            "PubChem adapter requires logger but none was provided. "
            "Ensure logger is passed from Composition Root."
        )

    # Get configuration parameters
    rate = kwargs.pop("rate", 5.0)  # 5 req/sec per RULES.md
    capacity = kwargs.pop("capacity", int(rate * 2))
    circuit_breaker_threshold = kwargs.pop("circuit_breaker_threshold", 5)
    circuit_breaker_timeout = kwargs.pop("circuit_breaker_timeout", 300)
    max_workers = kwargs.pop("max_workers", 4)
    strict_error_handling = kwargs.pop("strict_error_handling", False)

    # Create dependencies in Composition Root (DI pattern)
    rate_limiter = TokenBucket(rate=rate, capacity=capacity, provider="pubchem")
    circuit_breaker = CircuitBreaker(
        provider="pubchem",
        failure_threshold=circuit_breaker_threshold,
        recovery_timeout=circuit_breaker_timeout,
    )
    thread_pool = ThreadPoolExecutor(max_workers=max_workers)

    # Create adapter with injected dependencies
    return PubChemAdapter(
        logger=logger,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        thread_pool=thread_pool,
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
    # Create adapter via custom creator with all dependencies injected
    data_source = _create_pubchem_adapter(
        http_client=None,
        logger=logger,
        settings=settings,
        rate=5.0,
        strict_error_handling=settings.strict_error_handling,
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


# =============================================================================
# Provider registration
# =============================================================================


def register_all_providers() -> None:
    """Explicitly register all data source providers.

    This function MUST be called from bootstrap before using ProviderRegistry.
    Idempotent - safe to call multiple times.

    Provider configurations:
    - ChEMBL: 10 req/sec, capacity 20 (async HTTP client)
    - PubChem: 5 req/sec, capacity 10 (sync via ThreadPoolExecutor)
    - UniProt: 10 req/sec, 100 with API key, capacity 20 (async HTTP client)
    - PubMed: 3 req/sec, 10 with API key, capacity 6 (async HTTP client)

    Each provider now includes a data_source_creator for unified registry access.
    """
    # ChEMBL - async HTTP adapter
    if not ProviderRegistry.is_registered("chembl"):
        ProviderRegistry.register(
            "chembl",
            ProviderConfig(
                adapter_class=ChemblAdapter,
                http_config=HttpConfig(
                    rate=10.0,
                    capacity=20,
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
                    rate=5.0,
                    capacity=10,
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
                    rate=10.0,
                    capacity=20,
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
                    rate=3.0,
                    capacity=6,
                    rate_overrides={"pubmed_api_key": 10.0},
                ),
                requires_http_client=True,
                requires_logger=True,
                custom_creator=_create_pubmed_adapter,
                data_source_creator=_create_pubmed_data_source,
            ),
        )
