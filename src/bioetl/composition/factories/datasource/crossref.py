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


def _resolve_mailto(kwargs: dict[str, Any], settings: Settings | None) -> str:
    mailto = kwargs.get("mailto")
    if not mailto and settings:
        mailto = getattr(settings, "default_email", None)
    if not mailto:
        raise ValueError(
            "CrossRef adapter requires mailto. "
            "Provide via 'mailto' kwarg or settings.default_email"
        )
    return str(mailto)


def _resolve_helpers(
    kwargs: dict[str, Any], logger: LoggerPort, metrics: Any
) -> tuple[Any, Any, Any, Any]:
    helper_services = AdapterHelpersFactory.create_http_helpers(
        provider="crossref",
        logger=logger,
        metrics=metrics,
    )
    error_handler = kwargs.get("error_handler", helper_services.error_handler)
    adapter_metrics = kwargs.get("adapter_metrics", helper_services.adapter_metrics)
    request_collector = kwargs.get(
        "request_collector", helper_services.request_collector
    )
    fallback_fetch_service = kwargs.get(
        "fallback_fetch_service", helper_services.fallback_fetch_service
    )
    return error_handler, adapter_metrics, request_collector, fallback_fetch_service


def create_crossref_adapter(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: Settings | None,
    **kwargs: Any,
) -> CrossRefAdapter:
    """Create CrossRefAdapter resolving mandatory ``mailto`` from kwargs/settings."""
    if http_client is None:
        raise ValueError("CrossRef adapter requires http_client")
    if logger is None:
        raise ValueError("CrossRef adapter requires logger")

    mailto = _resolve_mailto(kwargs, settings)
    metrics = kwargs.get("metrics")
    error_handler, adapter_metrics, request_collector, fallback_fetch_service = (
        _resolve_helpers(kwargs, logger, metrics)
    )

    query_builder = kwargs.get(
        "query_builder"
    ) or _create_default_crossref_query_builder(
        api_base=CROSSREF_API_BASE, mailto=mailto
    )

    response_mapper = (
        kwargs.get("response_mapper") or _create_default_crossref_response_mapper()
    )

    batch_fetcher = kwargs.get(
        "batch_fetcher"
    ) or _create_default_crossref_batch_fetcher(
        http=http_client,
        logger=logger,
        metrics=adapter_metrics,
        mailto=mailto,
        api_base=CROSSREF_API_BASE,
        headers_fn=query_builder.build_headers,
        request_collector=request_collector,
    )

    search_paginator = kwargs.get(
        "search_paginator"
    ) or _create_default_crossref_search_paginator(
        http=http_client,
        logger=logger,
        metrics=adapter_metrics,
        mailto=mailto,
        api_base=CROSSREF_API_BASE,
        headers_fn=query_builder.build_headers,
        request_collector=request_collector,
    )

    title_fallback_handler = kwargs.get(
        "title_fallback_handler"
    ) or _create_default_crossref_title_fallback_handler(
        logger=logger,
        search_fn=search_paginator.search,
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
        query_builder=query_builder,
        response_mapper=response_mapper,
        batch_fetcher=batch_fetcher,
        search_paginator=search_paginator,
        title_fallback_handler=title_fallback_handler,
        fetch_flow=kwargs.get("fetch_flow"),
    )
