"""Data source creators for bibliographic providers extracted from registration.py."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any
from bioetl.composition.factories.datasource.crossref import (
    create_crossref_adapter,
)
from bioetl.composition.providers._config_helpers import (
    _create_http_data_source,
    _get_batch_size_from_config,
    _get_rate_limit_from_config,
    _normalize_optional_override,
)
from bioetl.composition.providers._registration_biblio_adapters import (
    _build_openalex_adapter_from_settings,
    _build_pubmed_adapter_from_settings,
)
from bioetl.composition.providers._models import HttpConfig, ProviderConfig
from bioetl.composition.providers._registration_contracts import (
    ProviderAssemblySupport,
    create_provider_assembly_support,
)
from bioetl.infrastructure.adapters.crossref import CrossRefAdapter
from bioetl.infrastructure.adapters.openalex import OpenAlexAdapter
from bioetl.infrastructure.adapters.pubmed import PubMedAdapter
from bioetl.infrastructure.adapters.semanticscholar import SemanticScholarAdapter

if TYPE_CHECKING:
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _create_pubmed_adapter_from_settings(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: Settings | None,
    **kwargs: Any,
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
    settings: Settings | None,
    **kwargs: Any,
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
    settings: Settings,
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
    configured_api_key = _normalize_optional_override(pipeline_config.source.api_key)
    settings_api_key = (
        settings.pubmed_api_key.get_secret_value() if settings.pubmed_api_key else None
    )
    api_key = configured_api_key or settings_api_key

    configured_email = _normalize_optional_override(pipeline_config.source.email)
    email = configured_email or settings.default_email

    return _create_http_data_source(
        provider="pubmed",
        settings=settings,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
        adapter_factory=PubMedAdapter,
        extra_kwargs={"email": email, "api_key": api_key},
        assembly_support=assembly_support,
    )


def _create_crossref_data_source(
    settings: Settings,
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
    configured_email = _normalize_optional_override(pipeline_config.source.email)
    mailto = configured_email or settings.default_email
    batch_size = _get_batch_size_from_config("crossref", default=50)

    return _create_http_data_source(
        provider="crossref",
        settings=settings,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
        adapter_factory=create_crossref_adapter,
        extra_kwargs={"settings": settings, "mailto": mailto, "batch_size": batch_size},
        assembly_support=assembly_support,
    )


def _create_openalex_data_source(
    settings: Settings,
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
    configured_email = _normalize_optional_override(pipeline_config.source.email)
    mailto = configured_email or settings.default_email
    batch_size = _get_batch_size_from_config("openalex", default=50)

    return _create_http_data_source(
        provider="openalex",
        settings=settings,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
        adapter_factory=OpenAlexAdapter,
        extra_kwargs={"mailto": mailto, "batch_size": batch_size},
        assembly_support=assembly_support,
    )


def _create_semanticscholar_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> DataSourcePort:
    """Create Semantic Scholar adapter and optionally wrap it with input filtering."""
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

    return _create_http_data_source(
        provider="semanticscholar",
        settings=settings,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
        adapter_factory=SemanticScholarAdapter,
        extra_kwargs={"api_key": api_key, "batch_size": batch_size},
        assembly_support=assembly_support,
    )


def _get_biblio_provider_configs(
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> dict[str, ProviderConfig]:
    """Build ProviderConfig entries for bibliographic providers."""
    support = assembly_support or create_provider_assembly_support()
    pubmed = _get_rate_limit_from_config("pubmed")
    crossref = _get_rate_limit_from_config("crossref")
    openalex = _get_rate_limit_from_config("openalex")
    semanticscholar = _get_rate_limit_from_config("semanticscholar")

    return {
        "pubmed": ProviderConfig(
            adapter_class=PubMedAdapter,
            http_config=HttpConfig(
                rate=pubmed.rate,
                capacity=pubmed.capacity,
                rate_overrides={"pubmed_api_key": 10.0},
            ),
            requires_http_client=True,
            requires_logger=True,
            custom_creator=_create_pubmed_adapter_from_settings,
            data_source_creator=partial(
                _create_pubmed_data_source,
                assembly_support=support,
            ),
        ),
        "crossref": ProviderConfig(
            adapter_class=CrossRefAdapter,
            http_config=HttpConfig(rate=crossref.rate, capacity=crossref.capacity),
            requires_http_client=True,
            requires_logger=True,
            custom_creator=create_crossref_adapter,
            data_source_creator=partial(
                _create_crossref_data_source,
                assembly_support=support,
            ),
        ),
        "openalex": ProviderConfig(
            adapter_class=OpenAlexAdapter,
            http_config=HttpConfig(rate=openalex.rate, capacity=openalex.capacity),
            requires_http_client=True,
            requires_logger=True,
            custom_creator=_create_openalex_adapter_from_settings,
            data_source_creator=partial(
                _create_openalex_data_source,
                assembly_support=support,
            ),
        ),
        "semanticscholar": ProviderConfig(
            adapter_class=SemanticScholarAdapter,
            http_config=HttpConfig(
                rate=semanticscholar.rate,
                capacity=semanticscholar.capacity,
            ),
            requires_http_client=True,
            requires_logger=True,
            data_source_creator=partial(
                _create_semanticscholar_data_source,
                assembly_support=support,
            ),
        ),
    }
