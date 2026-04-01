"""Data source creators for bibliographic providers extracted from registration.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.factories.datasource.crossref import (
    create_crossref_adapter,
)
from bioetl.composition.providers._config_helpers import (
    _build_provider_family_http_config_map,
    _create_http_data_source,
    _get_batch_size_from_config,
    _get_rate_limits_from_config,
)
from bioetl.composition.providers._models import (
    ProviderConfig,
    ProviderSettingsProtocol,
)
from bioetl.composition.providers._registration_biblio_adapters import (
    _build_openalex_adapter_from_settings,
    _build_pubmed_adapter_from_settings,
)
from bioetl.composition.providers._registration_biblio_profiles import (
    _resolve_mailto_batch_profile,
    _resolve_pubmed_request_profile,
    _resolve_semanticscholar_request_profile,
)
from bioetl.composition.providers._registration_contracts import (
    HttpProviderConfigSpec,
    ProviderAssemblySupport,
    resolve_provider_assembly_support,
)
from bioetl.infrastructure.adapters.crossref import CrossRefAdapter
from bioetl.infrastructure.adapters.openalex import OpenAlexAdapter
from bioetl.infrastructure.adapters.pubmed import PubMedAdapter
from bioetl.infrastructure.adapters.semanticscholar import SemanticScholarAdapter

if TYPE_CHECKING:
    from bioetl.composition.bootstrap_contexts import RateLimitContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _create_pubmed_adapter_from_settings(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: ProviderSettingsProtocol | None,
    **kwargs: object,
) -> PubMedAdapter:
    """Create PubMedAdapter with patch-friendly composition-local adapter binding."""
    return _build_pubmed_adapter_from_settings(
        adapter_cls=PubMedAdapter,
        http_client=http_client,
        logger=logger,
        settings=settings,
        **kwargs,
    )


def _create_openalex_adapter_from_settings(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: ProviderSettingsProtocol | None,
    **kwargs: object,
) -> OpenAlexAdapter:
    """Create OpenAlexAdapter with patch-friendly composition-local adapter binding."""
    return _build_openalex_adapter_from_settings(
        adapter_cls=OpenAlexAdapter,
        http_client=http_client,
        logger=logger,
        settings=settings,
        **kwargs,
    )


def _create_pubmed_data_source(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> DataSourcePort:
    """Create PubMed data source with optional CSV filtering.

    PubMed requires an email address and optionally an API key for higher rate
    limits (10 req/sec with key vs 3 req/sec without). The API key is resolved
    with the following priority:

    1. ``pipeline_config.source.api_key`` -- per-pipeline override (highest).
    2. ``settings.pubmed_api_key`` -- application-wide setting from
       ``BIOETL_PUBMED_API_KEY`` env var (fallback).
    3. ``None`` -- unauthenticated access with lower rate limits.

    Email follows a similar resolution: ``pipeline_config.source.email`` takes
    precedence over ``settings.default_email``.
    """
    profile = _resolve_pubmed_request_profile(settings, pipeline_config)

    return _create_http_data_source(
        provider="pubmed",
        settings=settings,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
        adapter_factory=PubMedAdapter,
        extra_kwargs={"email": profile.email, "api_key": profile.api_key},
        assembly_support=assembly_support,
    )


def _create_crossref_data_source(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> DataSourcePort:
    """Create CrossRef data source with optional CSV filtering.

    CrossRef requires mailto for polite pool access (50 req/sec vs 1 req/sec).
    Email is obtained from pipeline config or settings.default_email.
    """
    profile = _resolve_mailto_batch_profile(
        settings,
        pipeline_config,
        batch_size=_get_batch_size_from_config("crossref", default=50),
    )

    return _create_http_data_source(
        provider="crossref",
        settings=settings,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
        adapter_factory=create_crossref_adapter,
        extra_kwargs={
            "settings": settings,
            "mailto": profile.mailto,
            "batch_size": profile.batch_size,
        },
        assembly_support=assembly_support,
    )


def _create_openalex_data_source(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> DataSourcePort:
    """Create OpenAlex data source with optional CSV filtering.

    OpenAlex requires mailto for polite pool access (10 req/sec).
    Email is obtained from pipeline config or settings.default_email.
    """
    profile = _resolve_mailto_batch_profile(
        settings,
        pipeline_config,
        batch_size=_get_batch_size_from_config("openalex", default=50),
    )

    return _create_http_data_source(
        provider="openalex",
        settings=settings,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
        adapter_factory=OpenAlexAdapter,
        extra_kwargs={"mailto": profile.mailto, "batch_size": profile.batch_size},
        assembly_support=assembly_support,
    )


def _create_semanticscholar_data_source(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> DataSourcePort:
    """Create Semantic Scholar adapter and optionally wrap it with input filtering."""
    profile = _resolve_semanticscholar_request_profile(
        settings,
        batch_size=_get_batch_size_from_config("semanticscholar", default=100),
    )
    api_key = profile.api_key
    if not api_key:
        logger.warning(
            "semanticscholar_no_api_key",
            message="No API key provided. Rate limits will be shared with other users.",
        )

    return _create_http_data_source(
        provider="semanticscholar",
        settings=settings,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
        adapter_factory=SemanticScholarAdapter,
        extra_kwargs={"api_key": api_key, "batch_size": profile.batch_size},
        assembly_support=assembly_support,
    )


def _build_biblio_http_provider_specs(
    rate_limits: dict[str, RateLimitContext],
) -> tuple[HttpProviderConfigSpec, ...]:
    """Build the declarative HTTP provider manifest for the biblio family."""
    pubmed = rate_limits["pubmed"]
    crossref = rate_limits["crossref"]
    openalex = rate_limits["openalex"]
    semanticscholar = rate_limits["semanticscholar"]

    return (
        HttpProviderConfigSpec(
            provider_name="pubmed",
            adapter_class=PubMedAdapter,
            rate=pubmed.rate,
            capacity=pubmed.capacity,
            rate_overrides={"pubmed_api_key": 10.0},
            custom_creator=_create_pubmed_adapter_from_settings,
            data_source_creator=_create_pubmed_data_source,
        ),
        HttpProviderConfigSpec(
            provider_name="crossref",
            adapter_class=CrossRefAdapter,
            rate=crossref.rate,
            capacity=crossref.capacity,
            custom_creator=create_crossref_adapter,
            data_source_creator=_create_crossref_data_source,
        ),
        HttpProviderConfigSpec(
            provider_name="openalex",
            adapter_class=OpenAlexAdapter,
            rate=openalex.rate,
            capacity=openalex.capacity,
            custom_creator=_create_openalex_adapter_from_settings,
            data_source_creator=_create_openalex_data_source,
        ),
        HttpProviderConfigSpec(
            provider_name="semanticscholar",
            adapter_class=SemanticScholarAdapter,
            rate=semanticscholar.rate,
            capacity=semanticscholar.capacity,
            data_source_creator=_create_semanticscholar_data_source,
        ),
    )


def _get_biblio_provider_configs(
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> dict[str, ProviderConfig]:
    """Build ProviderConfig entries for bibliographic providers."""
    support = resolve_provider_assembly_support(assembly_support)
    rate_limits = _get_rate_limits_from_config(
        "pubmed",
        "crossref",
        "openalex",
        "semanticscholar",
    )
    return _build_provider_family_http_config_map(
        rate_limits=rate_limits,
        assembly_support=support,
        spec_builder=_build_biblio_http_provider_specs,
    )
