"""Explicit provider registration for Composition layer.

Loads config from configs/sources/*.yaml. HttpConfig serves as fallback.
"""

from __future__ import annotations

import logging
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
from bioetl.infrastructure.config import load_source_config

if TYPE_CHECKING:
    from bioetl.domain.filter_config import InputFilterConfig
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


def _get_page_size_from_config(provider: str, default: int = 1000) -> int:
    """Get page size from config for paginated APIs (e.g., ChEMBL)."""
    source_config = _get_source_config(provider)
    if source_config and source_config.page_size is not None:
        return source_config.page_size
    return default


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
    """Create ChEMBL data source with optional CSV filtering."""
    DataSourceFactory, HttpClientFactory = _get_factories()
    http_client = HttpClientFactory.create_for_provider("chembl", settings)
    page_size = _get_page_size_from_config("chembl", default=1000)
    filter_batch_size = _get_batch_size_from_config("chembl", default=20)
    base_adapter = DataSourceFactory.create(
        "chembl",
        http_client=http_client,
        logger=logger,
        batch_size=page_size,
        filter_batch_size=filter_batch_size,
        metrics=metrics,
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

    Each provider includes a data_source_creator for unified registry access.
    """
    # Load rate limits from source configs (with fallback defaults)
    chembl_rate, chembl_capacity = _get_rate_limit_from_config("chembl")
    pubchem_rate, pubchem_capacity = _get_rate_limit_from_config("pubchem")
    uniprot_rate, uniprot_capacity = _get_rate_limit_from_config("uniprot")
    pubmed_rate, pubmed_capacity = _get_rate_limit_from_config("pubmed")

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
