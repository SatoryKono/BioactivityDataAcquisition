"""Data source creators for bibliographic providers: PubMed, CrossRef, OpenAlex, SemanticScholar.

Extracted from registration.py for LOC compliance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.providers._config_helpers import (
    _get_batch_size_from_config,
    _get_factories,
    _normalize_optional_override,
    _wrap_with_filter,
)
from bioetl.composition.providers.factory_loader import (
    get_data_source_factory,
    get_http_client_factory,
)
from bioetl.infrastructure.adapters.crossref.client import _create_crossref_adapter
from bioetl.infrastructure.adapters.openalex.client import _create_openalex_adapter
from bioetl.infrastructure.adapters.pubmed.pubmed_client import PubMedAdapter
from bioetl.infrastructure.adapters.semanticscholar.adapter import (
    SemanticScholarAdapter,
)

if TYPE_CHECKING:
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _create_pubmed_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
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
    _, HttpClientFactory = _get_factories(
        get_data_source_factory, get_http_client_factory
    )
    http_client = HttpClientFactory.create_for_provider(
        "pubmed", settings, metrics=metrics
    )

    # Determine API key: config takes precedence over settings
    configured_api_key = _normalize_optional_override(pipeline_config.source.api_key)
    settings_api_key = (
        settings.pubmed_api_key.get_secret_value() if settings.pubmed_api_key else None
    )
    api_key = configured_api_key or settings_api_key

    configured_email = _normalize_optional_override(pipeline_config.source.email)
    email = configured_email or settings.default_email

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
    """
    _, HttpClientFactory = _get_factories(
        get_data_source_factory, get_http_client_factory
    )
    http_client = HttpClientFactory.create_for_provider("crossref", settings)

    # Get mailto from pipeline config or settings
    configured_email = _normalize_optional_override(pipeline_config.source.email)
    mailto = configured_email or settings.default_email
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
    """
    _, HttpClientFactory = _get_factories(
        get_data_source_factory, get_http_client_factory
    )
    http_client = HttpClientFactory.create_for_provider("openalex", settings)

    # Get mailto from pipeline config or settings
    configured_email = _normalize_optional_override(pipeline_config.source.email)
    mailto = configured_email or settings.default_email
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
    """Create Semantic Scholar adapter and optionally wrap it with input filtering."""
    _, HttpClientFactory = _get_factories(
        get_data_source_factory, get_http_client_factory
    )
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
