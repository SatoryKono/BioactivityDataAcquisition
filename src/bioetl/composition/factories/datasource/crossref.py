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


def _resolve_mailto(
    kwargs: dict[str, Any],
    settings: Settings | None,
) -> str:
    """Resolve mailto from kwargs or settings."""
    mailto = kwargs.get("mailto")
    if not mailto and settings:
        mailto = getattr(settings, "default_email", None)
    if not mailto:
        raise ValueError(
            "CrossRef adapter requires mailto. "
            "Provide via 'mailto' kwarg or settings.default_email"
        )
    return mailto


def _validate_dependencies(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
) -> None:
    """Validate required dependencies."""
    if http_client is None:
        raise ValueError("CrossRef adapter requires http_client")
    if logger is None:
        raise ValueError("CrossRef adapter requires logger")


def _create_helper_services(
    logger: LoggerPort,
    metrics: Any | None,
) -> Any:
    """Create helper services for the adapter."""
    return AdapterHelpersFactory.create_http_helpers(
        provider="crossref",
        logger=logger,
        metrics=metrics,
    )


def _resolve_optional_components(
    kwargs: dict[str, Any],
    helper_services: Any,
) -> tuple[Any, ...]:
    """Resolve optional components with defaults."""
    return (
        kwargs.get("error_handler", helper_services.error_handler),
        kwargs.get("adapter_metrics", helper_services.adapter_metrics),
        kwargs.get("request_collector", helper_services.request_collector),
        kwargs.get("fallback_fetch_service", helper_services.fallback_fetch_service),
    )


def _create_query_builder(
    kwargs: dict[str, Any],
    mailto: str,
) -> Any:
    """Create query builder with defaults."""
    query_builder = kwargs.get("query_builder")
    if query_builder is None:
        query_builder = _create_default_crossref_query_builder(
            api_base=CROSSREF_API_BASE,
            mailto=mailto,
        )
    return query_builder


def _create_response_mapper(
    kwargs: dict[str, Any],
) -> Any:
    """Create response mapper with defaults."""
    response_mapper = kwargs.get("response_mapper")
    if response_mapper is None:
        response_mapper = _create_default_crossref_response_mapper()
    return response_mapper


def _create_batch_fetcher(
    http_client: UnifiedHTTPClient,
    logger: LoggerPort,
    adapter_metrics: Any,
    mailto: str,
    headers_fn: Callable[..., dict[str, str]],
    request_collector: Any,
) -> Any:
    """Create batch fetcher with defaults."""
    batch_fetcher = kwargs.get("batch_fetcher")
    if batch_fetcher is None:
        batch_fetcher = _create_default_crossref_batch_fetcher(
            http=http_client,
            logger=logger,
            metrics=adapter_metrics,
            mailto=mailto,
            api_base=CROSSREF_API_BASE,
            headers_fn=headers_fn,
            request_collector=request_collector,
        )
    return batch_fetcher


def _create_search_paginator(
    http_client: UnifiedHTTPClient,
    logger: LoggerPort,
    adapter_metrics: Any,
    mailto: str,
    headers_fn: Callable[..., dict[str, str]],
    request_collector: Any,
) -> Any:
    """Create search paginator with defaults."""
    search_paginator = kwargs.get("search_paginator")
    if search_paginator is None:
        search_paginator = _create_default_crossref_search_paginator(
            http=http_client,
            logger=logger,
            metrics=adapter_metrics,
            mailto=mailto,
            api_base=CROSSREF_API_BASE,
            headers_fn=headers_fn,
            request_collector=request_collector,
        )
    return search_paginator


def _create_title_fallback_handler(
    logger: LoggerPort,
    search_fn: Callable[..., Any],
) -> Any:
    """Create title fallback handler with defaults."""
    title_fallback_handler = kwargs.get("title_fallback_handler")
    if title_fallback_handler is None:
        title_fallback_handler = _create_default_crossref_title_fallback_handler(
            logger=logger,
            search_fn=search_fn,
        )
    return title_fallback_handler


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
    # Resolve and validate dependencies
    mailto = _resolve_mailto(kwargs, settings)
    _validate_dependencies(http_client, logger)
    
    # Create helper services
    metrics = kwargs.get("metrics")
    helper_services = _create_helper_services(logger, metrics)
    
    # Resolve optional components
    error_handler, adapter_metrics, request_collector, fallback_fetch_service = \
        _resolve_optional_components(kwargs, helper_services)
    
    # Create query builder and get headers function
    query_builder = _create_query_builder(kwargs, mailto)
    headers_fn = query_builder.build_headers
    
    # Create response mapper
    response_mapper = _create_response_mapper(kwargs)
    
    # Create batch fetcher
    batch_fetcher = _create_batch_fetcher(
        http_client, logger, adapter_metrics, mailto, headers_fn, request_collector
    )
    
    # Create search paginator
    search_paginator = _create_search_paginator(
        http_client, logger, adapter_metrics, mailto, headers_fn, request_collector
    )
    
    # Create title fallback handler
    title_fallback_handler = _create_title_fallback_handler(logger, search_paginator.search)

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
