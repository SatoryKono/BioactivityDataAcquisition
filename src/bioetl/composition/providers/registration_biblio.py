"""Data source creators for bibliographic providers extracted from registration.py."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from bioetl.composition.factories.datasource.crossref import (
    create_crossref_adapter,
)
from bioetl.composition.providers._config_helpers import (
    _build_provider_family_config_map,
    _create_http_data_source,
    _get_batch_size_from_config,
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
    _resolve_openalex_request_profile,
    _resolve_pubmed_request_profile,
    _resolve_semanticscholar_request_profile,
)
from bioetl.composition.providers._models import AdapterCreatorProtocol
from bioetl.composition.providers._registration_contracts import (
    HttpProviderConfigSpec,
    ProviderAssemblySupport,
    build_http_provider_config_spec,
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
    only from ``settings.pubmed_api_key`` (``BIOETL_PUBMED_API_KEY`` /
    ``provider_config.api_key_env``). ``pipeline.source.api_key`` is rejected.

    Email may still come from ``pipeline_config.source.email``, falling back to
    ``settings.default_email``.
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


def _create_mailto_batch_data_source(
    *,
    provider: str,
    adapter_factory: Callable[..., DataSourcePort],
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None,
    metrics: MetricsPort | None,
    pipeline_name: str,
    default_batch_size: int,
    assembly_support: ProviderAssemblySupport | None,
    include_settings: bool = False,
) -> DataSourcePort:
    """Create a mailto/batch driven HTTP data source for biblio providers."""
    profile = _resolve_mailto_batch_profile(
        settings,
        pipeline_config,
        batch_size=_get_batch_size_from_config(provider, default=default_batch_size),
    )
    extra_kwargs: dict[str, object] = {
        "mailto": profile.mailto,
        "batch_size": profile.batch_size,
    }
    if include_settings:
        extra_kwargs["settings"] = settings
    return _create_http_data_source(
        provider=provider,
        settings=settings,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
        adapter_factory=adapter_factory,
        extra_kwargs=extra_kwargs,
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
    """Create CrossRef data source with optional CSV filtering."""
    return _create_mailto_batch_data_source(
        provider="crossref",
        adapter_factory=create_crossref_adapter,
        settings=settings,
        pipeline_config=pipeline_config,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
        default_batch_size=50,
        assembly_support=assembly_support,
        include_settings=True,
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
    """Create OpenAlex data source with optional CSV filtering."""
    profile = _resolve_openalex_request_profile(
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
        extra_kwargs={
            "api_key": profile.api_key,
            "mailto": profile.mailto,
            "batch_size": profile.batch_size,
        },
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
        build_http_provider_config_spec(
            provider_name="pubmed",
            adapter_class=PubMedAdapter,
            rate=pubmed.rate,
            capacity=pubmed.capacity,
            adapter_creator=cast(
                AdapterCreatorProtocol,
                _create_pubmed_adapter_from_settings,
            ),
            data_source_creator=_create_pubmed_data_source,
        ),
        build_http_provider_config_spec(
            provider_name="crossref",
            adapter_class=CrossRefAdapter,
            rate=crossref.rate,
            capacity=crossref.capacity,
            adapter_creator=cast(AdapterCreatorProtocol, create_crossref_adapter),
            data_source_creator=_create_crossref_data_source,
        ),
        build_http_provider_config_spec(
            provider_name="openalex",
            adapter_class=OpenAlexAdapter,
            rate=openalex.rate,
            capacity=openalex.capacity,
            adapter_creator=cast(
                AdapterCreatorProtocol,
                _create_openalex_adapter_from_settings,
            ),
            data_source_creator=_create_openalex_data_source,
        ),
        build_http_provider_config_spec(
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
    return _build_provider_family_config_map(
        "pubmed",
        "crossref",
        "openalex",
        "semanticscholar",
        assembly_support=assembly_support,
        http_spec_builder=_build_biblio_http_provider_specs,
    )
