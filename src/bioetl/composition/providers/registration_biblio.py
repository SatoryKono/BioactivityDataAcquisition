"""Data source creators for bibliographic providers: PubMed, CrossRef, OpenAlex, SemanticScholar.

Extracted from registration.py for LOC compliance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.providers._config_helpers import (
    _create_http_data_source,
    _get_batch_size_from_config,
    _get_rate_limit_from_config,
    _normalize_optional_override,
)
from bioetl.composition.providers.provider_registry import (
    HttpConfig,
    ProviderConfig,
)
from bioetl.infrastructure.adapters.crossref.client import CrossRefAdapter
from bioetl.infrastructure.adapters.crossref.factory import _create_crossref_adapter
from bioetl.infrastructure.adapters.openalex.client import (
    OpenAlexAdapter,
    _create_openalex_adapter,
)
from bioetl.infrastructure.adapters.pubmed.pubmed_client import (
    PubMedAdapter,
    _create_pubmed_adapter,
)
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
    )


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
        adapter_factory=_create_crossref_adapter,
        extra_kwargs={"settings": settings, "mailto": mailto, "batch_size": batch_size},
    )


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
        adapter_factory=_create_openalex_adapter,
        extra_kwargs={"settings": settings, "mailto": mailto, "batch_size": batch_size},
    )


def _create_semanticscholar_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
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
    )


def _get_biblio_provider_configs() -> dict[str, ProviderConfig]:
    """Build ProviderConfig entries for bibliographic providers."""
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
            custom_creator=_create_pubmed_adapter,
            data_source_creator=_create_pubmed_data_source,
        ),
        "crossref": ProviderConfig(
            adapter_class=CrossRefAdapter,
            http_config=HttpConfig(rate=crossref.rate, capacity=crossref.capacity),
            requires_http_client=True,
            requires_logger=True,
            custom_creator=_create_crossref_adapter,
            data_source_creator=_create_crossref_data_source,
        ),
        "openalex": ProviderConfig(
            adapter_class=OpenAlexAdapter,
            http_config=HttpConfig(rate=openalex.rate, capacity=openalex.capacity),
            requires_http_client=True,
            requires_logger=True,
            custom_creator=_create_openalex_adapter,
            data_source_creator=_create_openalex_data_source,
        ),
        "semanticscholar": ProviderConfig(
            adapter_class=SemanticScholarAdapter,
            http_config=HttpConfig(
                rate=semanticscholar.rate,
                capacity=semanticscholar.capacity,
            ),
            requires_http_client=True,
            requires_logger=True,
            data_source_creator=_create_semanticscholar_data_source,
        ),
    }
