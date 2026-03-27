"""CrossRef adapter factory for composition-layer wiring only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.composition.factories.datasource.adapter_helpers import (
    AdapterHelpersFactory,
)
from bioetl.infrastructure.adapters.crossref import CROSSREF_API_BASE, CrossRefAdapter
from bioetl.infrastructure.adapters.crossref.client_builders import (
    _create_default_crossref_batch_fetcher,
    _create_default_crossref_query_builder,
    _create_default_crossref_response_mapper,
    _create_default_crossref_search_paginator,
    _create_default_crossref_title_fallback_handler,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings

__all__ = ["create_crossref_adapter"]


def _resolve_core_components(kwargs: dict[str, Any], mailto: str) -> tuple[Any, Any]:
    query_builder = kwargs.get("query_builder") or _create_default_crossref_query_builder(
        api_base=CROSSREF_API_BASE, mailto=mailto
    )
    response_mapper = kwargs.get("response_mapper") or _create_default_crossref_response_mapper()
    return query_builder, response_mapper

def _resolve_fetchers(
    http_client: UnifiedHTTPClient, logger: LoggerPort, mailto: str,
    adapter_metrics: Any, request_collector: Any, kwargs: dict[str, Any], headers_fn: Any
) -> tuple[Any, Any]:
    batch_fetcher = kwargs.get("batch_fetcher") or _create_default_crossref_batch_fetcher(
        http=http_client, logger=logger, metrics=adapter_metrics, mailto=mailto,
        api_base=CROSSREF_API_BASE, headers_fn=headers_fn, request_collector=request_collector,
    )
    search_paginator = kwargs.get("search_paginator") or _create_default_crossref_search_paginator(
        http=http_client, logger=logger, metrics=adapter_metrics, mailto=mailto,
        api_base=CROSSREF_API_BASE, headers_fn=headers_fn, request_collector=request_collector,
    )
    return batch_fetcher, search_paginator

def _resolve_crossref_components(
    http_client: UnifiedHTTPClient, logger: LoggerPort, mailto: str,
    adapter_metrics: Any, request_collector: Any, kwargs: dict[str, Any]
) -> tuple[Any, Any, Any, Any, Any]:
    query_builder, response_mapper = _resolve_core_components(kwargs, mailto)
    batch_fetcher, search_paginator = _resolve_fetchers(
        http_client, logger, mailto, adapter_metrics, request_collector, kwargs, query_builder.build_headers
    )
    title_fallback = kwargs.get("title_fallback_handler") or _create_default_crossref_title_fallback_handler(
        logger=logger, search_fn=search_paginator.search
    )
    return query_builder, response_mapper, batch_fetcher, search_paginator, title_fallback


def create_crossref_adapter(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: Settings | None,
    **kwargs: Any,  # Any: forward arbitrary adapter config kwargs
) -> CrossRefAdapter:
    """Create CrossRefAdapter resolving mandatory ``mailto`` from kwargs/settings.

    Args:
        http_client: HTTP client for CrossRef API calls; raises ValueError if None.
        logger: LoggerPort for structured logging; raises ValueError if None.
        settings: Optional application settings used to resolve default_email as
            fallback mailto when not provided in kwargs.
        **kwargs: Additional adapter kwargs forwarded to CrossRefAdapter, including
            mailto, batch_size, metrics, error_handler, adapter_metrics,
            request_collector, fallback_fetch_service, and optional runtime
            collaborators.

    Returns:
        Configured CrossRefAdapter instance.

    Raises:
        ValueError: If mailto cannot be resolved or http_client/logger is None.
    """
    mailto = kwargs.get("mailto") or (getattr(settings, "default_email", None) if settings else None)
    if not mailto:
        raise ValueError(
            "CrossRef adapter requires mailto. "
            "Provide via 'mailto' kwarg or settings.default_email"
        )
    if http_client is None:
        raise ValueError("CrossRef adapter requires http_client")
    if logger is None:
        raise ValueError("CrossRef adapter requires logger")

    metrics = kwargs.get("metrics")
    helper_services = AdapterHelpersFactory.create_http_helpers(
        provider="crossref", logger=logger, metrics=metrics
    )
    error_handler = kwargs.get("error_handler", helper_services.error_handler)
    adapter_metrics = kwargs.get("adapter_metrics", helper_services.adapter_metrics)
    request_collector = kwargs.get("request_collector", helper_services.request_collector)
    fallback_fetch_service = kwargs.get("fallback_fetch_service", helper_services.fallback_fetch_service)

    qb, rm, bf, sp, tfh = _resolve_crossref_components(
        http_client, logger, mailto, adapter_metrics, request_collector, kwargs
    )

    return CrossRefAdapter(
        http_client=http_client,
        logger=logger,
        mailto=mailto,
        batch_size=kwargs.get("batch_size", 50),
        metrics=metrics,
        dependency_context=kwargs.get("dependency_context"),
        error_handler=error_handler,
        adapter_metrics=adapter_metrics,
        request_collector=request_collector,
        fallback_fetch_service=fallback_fetch_service,
        query_builder=qb,
        response_mapper=rm,
        batch_fetcher=bf,
        search_paginator=sp,
        title_fallback_handler=tfh,
        fetch_flow=kwargs.get("fetch_flow"),
    )
