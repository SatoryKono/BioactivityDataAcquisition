# Boundary object/payload typing residual at this module.
"""Data source creators for bio providers: ChEMBL, PubChem, UniProt, IDMapping."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.data_sources.idmapping import IDMappingDataSource
from bioetl.application.core.data_sources.publication_term import (
    PublicationTermDataSource,
)
from bioetl.application.core.data_sources.subcellular_fraction import (
    SubcellularFractionDataSource,
)
from bioetl.composition.factories.datasource.adapter_helpers import (
    AdapterHelpersFactory,
)
from bioetl.composition.factories.datasource.pubchem import (
    create_pubchem_adapter,
)
from bioetl.composition.providers._config_helpers import (
    _build_provider_family_config_map,
    _get_adapter_config,
    _validate_extraction_input_filter_overlap,
    _wrap_with_filter,
)
from bioetl.composition.providers._models import (
    HttpConfig,
    ProviderConfig,
    ProviderSettingsProtocol,
)
from bioetl.composition.providers._registration_contracts import (
    HttpProviderConfigSpec,
    ProviderAssemblySupport,
    build_data_source_provider_config,
    build_http_provider_config_spec,
    resolve_provider_assembly_support,
)
from bioetl.composition.providers._chembl_target_protein_classification_data_source import (
    TargetProteinClassificationSnapshotDataSource,
)
from bioetl.domain.models.filter import ExtractionParams
from bioetl.infrastructure.adapters.chembl import ChemblAdapter
from bioetl.infrastructure.adapters.input import IDMappingCsvReaderAdapter
from bioetl.infrastructure.adapters.pubchem import PubChemAdapter
from bioetl.infrastructure.adapters.uniprot import UniProtAdapter
from bioetl.infrastructure.adapters.uniprot.constants import UNIPROT_API_BASE
from bioetl.infrastructure.adapters.uniprot.idmapping_client import (
    UniProtIDMappingClient,
)
from bioetl.infrastructure.storage.delta_reader import DeltaReader

if TYPE_CHECKING:
    from bioetl.composition.bootstrap_contexts import RateLimitContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _create_chembl_data_source(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> DataSourcePort:
    """Create ChEMBL data source with optional CSV filtering.

    Configuration is loaded from configs/providers/chembl.yaml via AdapterConfig.
    This ensures YAML is the single source of truth (RULES.md §12.1.2).

    For document_term entity type, wraps the adapter with PublicationTermDataSource
    to extract terms from publication records (derived entity pattern).
    """
    if pipeline_config.entity_type == "target_protein_classification":
        return _wrap_with_filter(
            TargetProteinClassificationSnapshotDataSource(
                delta_reader=DeltaReader(
                    base_path=settings.gold_path,
                    logger=logger,
                ),
                logger=logger,
            ),
            filter_config,
            logger,
            metrics,
            pipeline_name,
        )

    support = resolve_provider_assembly_support(assembly_support)
    http_client = support.create_http_client("chembl", settings, metrics=metrics)

    # Load adapter configuration from YAML (single source of truth)
    adapter_config = _get_adapter_config("chembl", default_page_size=1000)

    # Build ExtractionParams from pipeline config (ADR-028 §3)
    extraction_params = ExtractionParams(params=pipeline_config.extraction_params)

    # Validate overlap between extraction_params and input_filter
    if filter_config is not None:
        _validate_extraction_input_filter_overlap(
            extraction_params, filter_config, logger
        )

    base_adapter = support.create_adapter(
        "chembl",
        http_client=http_client,
        logger=logger,
        settings=settings,
        adapter_config=adapter_config,
        metrics=metrics,
        extraction_params=extraction_params,
    )

    # Wrap derived-entity pipelines with their record-shaping data sources.
    # publication_term is extracted from publication records (1:M relationship)
    if pipeline_config.entity_type == "publication_term":
        base_adapter = PublicationTermDataSource(base_adapter)
    if pipeline_config.entity_type == "subcellular_fraction":
        base_adapter = SubcellularFractionDataSource(base_adapter)  # pyright: ignore[reportArgumentType]

    return _wrap_with_filter(
        base_adapter,
        filter_config,
        logger,
        metrics,
        pipeline_name,  # pyright: ignore[reportArgumentType]
    )


def _create_pubchem_adapter(
    http_client: UnifiedHTTPClient | None = None,
    logger: LoggerPort | None = None,
    settings: ProviderSettingsProtocol | None = None,
    **kwargs: object,
) -> DataSourcePort:
    """Retained provider-registration wrapper for the PubChem composition factory."""
    return create_pubchem_adapter(
        http_client=http_client,
        logger=logger,
        settings=settings,
        **kwargs,
    )


def _create_pubchem_data_source(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create PubChem data source with composition-owned adapter wiring."""
    data_source = _create_pubchem_adapter(
        logger=logger,
        settings=settings,
        strict_error_handling=settings.strict_error_handling,
        metrics=metrics,
    )
    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _get_uniprot_api_key(settings: ProviderSettingsProtocol | None) -> str | None:
    """Return optional UniProt API key from settings when configured."""
    if settings is None or settings.uniprot_api_key is None:
        return None
    return settings.uniprot_api_key.get_secret_value()


def _create_uniprot_data_source(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> DataSourcePort:
    """Create UniProt data source with optional CSV filtering.

    UniProt uses the generic DataSourceFactory path with a UnifiedHTTPClient.
    The base URL defaults to ``https://rest.uniprot.org`` but can be overridden
    via ``pipeline_config.source.api.base_url`` for testing or alternative
    deployments.
    """
    support = resolve_provider_assembly_support(assembly_support)
    http_client = support.create_http_client("uniprot", settings, metrics=metrics)
    helper_services = AdapterHelpersFactory.create_http_helpers(
        provider="uniprot",
        logger=logger,
        metrics=metrics,
    )
    data_source = support.create_adapter(
        "uniprot",
        http_client=http_client,
        logger=logger,
        settings=settings,
        api_key=_get_uniprot_api_key(settings),
        base_url=pipeline_config.source.api.base_url or UNIPROT_API_BASE,
        strict_error_handling=settings.strict_error_handling,
        metrics=metrics,
        **helper_services.as_injection_kwargs(),
    )
    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _create_uniprot_idmapping_data_source(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> DataSourcePort:
    """Create UniProt ID Mapping data source.

    Creates an IDMappingDataSource that:
    1. Reads ChEMBL target IDs via an infrastructure source reader
    2. Calls UniProt ID Mapping API to map to UniProt accessions
    3. Yields records with mapping results
    """
    support = resolve_provider_assembly_support(assembly_support)
    http_client = support.create_http_client("uniprot", settings, metrics=metrics)
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
        return str(pipeline_config.source.api.base_url)
    return str(UNIPROT_API_BASE)


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


def _build_bio_http_provider_specs(
    rate_limits: dict[str, RateLimitContext],
) -> tuple[HttpProviderConfigSpec, ...]:
    """Build the declarative HTTP provider manifest for the bio family."""
    chembl = rate_limits["chembl"]
    uniprot = rate_limits["uniprot"]

    return (
        build_http_provider_config_spec(
            provider_name="chembl",
            adapter_class=ChemblAdapter,
            rate=chembl.rate,
            capacity=chembl.capacity,
            data_source_creator=_create_chembl_data_source,
        ),
        build_http_provider_config_spec(
            provider_name="uniprot",
            adapter_class=UniProtAdapter,
            rate=uniprot.rate,
            capacity=uniprot.capacity,
            rate_overrides={"uniprot_api_key": 100.0},
            data_source_creator=_create_uniprot_data_source,
        ),
        build_http_provider_config_spec(
            provider_name="uniprot_idmapping",
            adapter_class=IDMappingDataSource,
            rate=uniprot.rate,
            capacity=uniprot.capacity,
            data_source_creator=_create_uniprot_idmapping_data_source,
        ),
    )


def _build_bio_extra_provider_configs(
    rate_limits: dict[str, RateLimitContext],
    _assembly_support: ProviderAssemblySupport,
) -> dict[str, ProviderConfig]:
    """Build non-HTTP special-case provider configs for the bio family."""
    pubchem = rate_limits["pubchem"]

    return {
        "pubchem": build_data_source_provider_config(
            adapter_class=PubChemAdapter,
            http_config=HttpConfig(rate=pubchem.rate, capacity=pubchem.capacity),
            requires_http_client=False,
            requires_logger=True,
            adapter_creator=_create_pubchem_adapter,
            data_source_creator=_create_pubchem_data_source,
        ),
    }


def _get_bio_provider_configs(
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> dict[str, ProviderConfig]:
    """Build ProviderConfig entries for bio providers."""
    return _build_provider_family_config_map(
        "chembl",
        "pubchem",
        "uniprot",
        assembly_support=assembly_support,
        http_spec_builder=_build_bio_http_provider_specs,
        extra_config_builder=_build_bio_extra_provider_configs,
    )
