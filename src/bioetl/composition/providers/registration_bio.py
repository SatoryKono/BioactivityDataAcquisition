"""Data source creators for bio providers: ChEMBL, PubChem, UniProt, IDMapping.

Extracted from registration.py for LOC compliance.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, cast

from bioetl.application.core.idmapping_data_source import IDMappingDataSource
from bioetl.application.core.publication_term_data_source import (
    PublicationTermDataSource,
)
from bioetl.composition.factories.datasource.adapter_helpers import (
    AdapterHelpersFactory,
)
from bioetl.composition.providers._config_helpers import (
    _get_adapter_config,
    _get_circuit_breaker_from_config,
    _get_factories,
    _get_rate_limit_from_config,
    _validate_extraction_input_filter_overlap,
    _wrap_with_filter,
)
from bioetl.composition.providers.factory_loader import (
    get_data_source_factory,
    get_http_client_factory,
)
from bioetl.composition.providers.provider_registry import (
    HttpConfig,
    ProviderConfig,
)
from bioetl.domain.models.filter import ExtractionParams
from bioetl.infrastructure.adapters.chembl import ChemblAdapter
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.input import IDMappingCsvReaderAdapter
from bioetl.infrastructure.adapters.pubchem import PubChemAdapter
from bioetl.infrastructure.adapters.uniprot import UniProtAdapter
from bioetl.infrastructure.adapters.uniprot.constants import UNIPROT_API_BASE
from bioetl.infrastructure.adapters.uniprot.idmapping_client import (
    UniProtIDMappingClient,
)

if TYPE_CHECKING:
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _create_chembl_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create ChEMBL data source with optional CSV filtering.

    Configuration is loaded from configs/providers/chembl.yaml via AdapterConfig.
    This ensures YAML is the single source of truth (RULES.md §12.1.2).

    For document_term entity type, wraps the adapter with PublicationTermDataSource
    to extract terms from publication records (derived entity pattern).
    """
    DataSourceFactory, HttpClientFactory = _get_factories(
        get_data_source_factory, get_http_client_factory
    )
    http_client = HttpClientFactory.create_for_provider(
        "chembl", settings, metrics=metrics
    )

    # Load adapter configuration from YAML (single source of truth)
    adapter_config = _get_adapter_config("chembl", default_page_size=1000)

    # Build ExtractionParams from pipeline config (ADR-028 §3)
    extraction_params = ExtractionParams(params=pipeline_config.extraction_params)

    # Validate overlap between extraction_params and input_filter
    if filter_config is not None:
        _validate_extraction_input_filter_overlap(
            extraction_params, filter_config, logger
        )

    base_adapter = DataSourceFactory.create(
        "chembl",
        http_client=http_client,
        logger=logger,
        adapter_config=adapter_config,
        metrics=metrics,
        extraction_params=extraction_params,
    )

    # Wrap with PublicationTermDataSource for derived entity extraction
    # publication_term is extracted from publication records (1:M relationship)
    if pipeline_config.entity_type == "publication_term":
        base_adapter = PublicationTermDataSource(base_adapter)

    return _wrap_with_filter(
        base_adapter, filter_config, logger, metrics, pipeline_name
    )


def _create_pubchem_adapter(
    http_client: UnifiedHTTPClient | None = None,
    logger: LoggerPort | None = None,
    settings: Settings | None = None,
    **kwargs: object,
) -> DataSourcePort:
    """Create PubChem adapter with all dependencies injected from Composition Root."""
    if logger is None:
        raise ValueError("PubChem adapter requires logger")

    rate_limit = _get_rate_limit_from_config("pubchem")
    cb_config = _get_circuit_breaker_from_config("pubchem")
    rate = cast(float, kwargs.pop("rate", rate_limit.rate))
    capacity = cast(int, kwargs.pop("capacity", rate_limit.capacity))
    cb_threshold = cast(
        int, kwargs.pop("circuit_breaker_threshold", cb_config.failure_threshold)
    )
    cb_timeout = cast(
        int, kwargs.pop("circuit_breaker_timeout", cb_config.recovery_timeout)
    )
    max_workers = cast(int, kwargs.pop("max_workers", 4))
    strict_error_handling = cast(bool, kwargs.pop("strict_error_handling", False))
    metrics = cast("MetricsPort | None", kwargs.pop("metrics", None))

    return PubChemAdapter(
        logger=logger,
        rate_limiter=TokenBucketRateLimiter(
            rate=rate, capacity=capacity, provider="pubchem"
        ),
        circuit_breaker=CircuitBreakerGuard(
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
    """Create PubChem data source with optional filtering.

    PubChem adapter dependencies are assembled in `_create_pubchem_adapter`
    (Composition Root), then optionally wrapped with input filtering.
    """
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
    """Create UniProt data source with optional CSV filtering.

    UniProt uses the generic DataSourceFactory path with a UnifiedHTTPClient.
    The base URL defaults to ``https://rest.uniprot.org`` but can be overridden
    via ``pipeline_config.source.api.base_url`` for testing or alternative
    deployments.
    """
    DataSourceFactory, HttpClientFactory = _get_factories(
        get_data_source_factory, get_http_client_factory
    )
    http_client = HttpClientFactory.create_for_provider(
        "uniprot", settings, metrics=metrics
    )
    helper_services = AdapterHelpersFactory.create_http_helpers(
        provider="uniprot",
        logger=logger,
        metrics=metrics,
    )
    data_source = DataSourceFactory.create(
        "uniprot",
        http_client=http_client,
        logger=logger,
        base_url=pipeline_config.source.api.base_url or UNIPROT_API_BASE,
        strict_error_handling=settings.strict_error_handling,
        metrics=metrics,
        **helper_services.as_injection_kwargs(),
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
    1. Reads ChEMBL target IDs via an infrastructure source reader
    2. Calls UniProt ID Mapping API to map to UniProt accessions
    3. Yields records with mapping results
    """
    _, http_client_factory = _get_factories(
        get_data_source_factory, get_http_client_factory
    )
    http_client = http_client_factory.create_for_provider("uniprot", settings)
    from_db, to_db = _resolve_uniprot_mapping_databases(pipeline_config)
    return IDMappingDataSource(
        idmapping_client=UniProtIDMappingClient(
            http_client=http_client,
            logger=logger,
            metrics=metrics,
            base_url=_resolve_uniprot_mapping_base_url(pipeline_config),
        ),
        id_source_reader=IDMappingCsvReaderAdapter(logger=logger),
        input_path=_resolve_uniprot_mapping_input_path(pipeline_config),
        logger=logger,
        from_db=from_db,
        to_db=to_db,
        seed_ids=_extract_uniprot_mapping_seed_ids(filter_config),
    )


def _resolve_uniprot_mapping_base_url(pipeline_config: PipelineYamlConfig) -> str:
    """Resolve UniProt ID Mapping base URL from config with safe default."""
    if pipeline_config.source.api and pipeline_config.source.api.base_url:
        return pipeline_config.source.api.base_url
    return UNIPROT_API_BASE


def _resolve_uniprot_mapping_input_path(pipeline_config: PipelineYamlConfig) -> str:
    """Resolve input CSV path for UniProt ID Mapping seed IDs."""
    configured = getattr(pipeline_config.source, "input_path", None)
    return configured or "data/input/target.csv"


def _resolve_uniprot_mapping_databases(
    pipeline_config: PipelineYamlConfig,
) -> tuple[str, str]:
    """Resolve source/target database names for UniProt mapping API."""
    from_db = "ChEMBL"
    to_db = "UniProtKB"
    if pipeline_config.source.api:
        from_db = getattr(pipeline_config.source.api, "from_db", None) or from_db
        to_db = getattr(pipeline_config.source.api, "to_db", None) or to_db
    return from_db, to_db


def _extract_uniprot_mapping_seed_ids(
    filter_config: InputFilterConfig | None,
) -> list[str] | None:
    """Extract optional seed IDs from input filter config."""
    if filter_config and filter_config.direct_filter_ids:
        return list(filter_config.direct_filter_ids)
    return None


def _get_bio_provider_configs() -> dict[str, ProviderConfig]:
    """Build ProviderConfig entries for bio providers."""
    chembl = _get_rate_limit_from_config("chembl")
    pubchem = _get_rate_limit_from_config("pubchem")
    uniprot = _get_rate_limit_from_config("uniprot")

    return {
        "chembl": ProviderConfig(
            adapter_class=ChemblAdapter,
            http_config=HttpConfig(rate=chembl.rate, capacity=chembl.capacity),
            requires_http_client=True,
            requires_logger=True,
            data_source_creator=_create_chembl_data_source,
        ),
        "pubchem": ProviderConfig(
            adapter_class=PubChemAdapter,
            http_config=HttpConfig(rate=pubchem.rate, capacity=pubchem.capacity),
            requires_http_client=False,
            requires_logger=True,
            custom_creator=_create_pubchem_adapter,
            data_source_creator=_create_pubchem_data_source,
        ),
        "uniprot": ProviderConfig(
            adapter_class=UniProtAdapter,
            http_config=HttpConfig(
                rate=uniprot.rate,
                capacity=uniprot.capacity,
                rate_overrides={"uniprot_api_key": 100.0},
            ),
            requires_http_client=True,
            requires_logger=True,
            data_source_creator=_create_uniprot_data_source,
        ),
        "uniprot_idmapping": ProviderConfig(
            adapter_class=IDMappingDataSource,
            http_config=HttpConfig(rate=uniprot.rate, capacity=uniprot.capacity),
            requires_http_client=True,
            requires_logger=True,
            data_source_creator=_create_uniprot_idmapping_data_source,
        ),
    }
