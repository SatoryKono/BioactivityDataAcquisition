"""CrossRef adapter factory for composition-layer wiring only."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, cast

from bioetl.composition.factories.datasource.adapter_helpers import (
    AdapterHelperServices,
    AdapterHelpersFactory,
)
from bioetl.domain.ports import ErrorHandlerPort
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common import FallbackFetchOrchestratorService
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.crossref import CROSSREF_API_BASE, CrossRefAdapter
from bioetl.infrastructure.adapters.crossref._doi_batch_processor import (
    DoiBatchProcessor,
)
from bioetl.infrastructure.adapters.crossref._search_paginator import SearchPaginator
from bioetl.infrastructure.adapters.crossref.client_builders import (
    _create_default_crossref_batch_fetcher,
    _create_default_crossref_query_builder,
    _create_default_crossref_response_mapper,
    _create_default_crossref_search_paginator,
    _create_default_crossref_title_fallback_handler,
)
from bioetl.infrastructure.adapters.crossref.fallback import (
    CrossRefTitleFallbackHandler,
)
from bioetl.infrastructure.adapters.crossref.query_builder import CrossRefQueryBuilder
from bioetl.infrastructure.adapters.crossref.response_mapper import (
    CrossRefResponseMapper,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.common.dependency_context import (
        HttpAdapterDependencyContext,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.adapters.crossref.fetch_flow import CrossRefFetchFlow
    from bioetl.infrastructure.config import Settings

__all__ = ["create_crossref_adapter"]


def _resolve_mailto(
    kwargs: dict[str, object],
    settings: Settings | None,
) -> str:
    """Resolve mailto from kwargs or settings."""
    mailto_raw = kwargs.get("mailto")
    mailto = mailto_raw if isinstance(mailto_raw, str) and mailto_raw else None
    if not mailto and settings:
        mailto = getattr(settings, "default_email", None)
    if not mailto:
        raise ValueError(
            "CrossRef adapter requires mailto. "
            "Provide via 'mailto' kwarg or settings.default_email"
        )
    return mailto


def _require_dependencies(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
) -> tuple[UnifiedHTTPClient, LoggerPort]:
    """Validate and return required dependencies."""
    if http_client is None:
        raise ValueError("CrossRef adapter requires http_client")
    if logger is None:
        raise ValueError("CrossRef adapter requires logger")
    return http_client, logger


def _create_helper_services(
    logger: LoggerPort,
    metrics: MetricsPort | None,
) -> AdapterHelperServices:
    """Create helper services for the adapter."""
    return AdapterHelpersFactory.create_http_helpers(
        provider="crossref",
        logger=logger,
        metrics=metrics,
    )


def _resolve_optional_components(
    kwargs: dict[str, object],
    helper_services: AdapterHelperServices,
) -> tuple[
    ErrorHandlerPort,
    AdapterMetricsRecorder,
    APIRequestCollector,
    FallbackFetchOrchestratorService,
]:
    """Resolve optional components with defaults."""
    error_handler = cast("ErrorHandlerPort | None", kwargs.get("error_handler"))
    adapter_metrics = cast(
        "AdapterMetricsRecorder | None",
        kwargs.get("adapter_metrics"),
    )
    request_collector = cast(
        "APIRequestCollector | None",
        kwargs.get("request_collector"),
    )
    fallback_fetch_service = cast(
        "FallbackFetchOrchestratorService | None",
        kwargs.get("fallback_fetch_service"),
    )
    return (
        error_handler or helper_services.error_handler,
        adapter_metrics or helper_services.adapter_metrics,
        request_collector or helper_services.request_collector,
        fallback_fetch_service or helper_services.fallback_fetch_service,
    )


def _create_query_builder(
    kwargs: dict[str, object],
    mailto: str,
) -> CrossRefQueryBuilder:
    """Create query builder with defaults."""
    query_builder = cast(
        "CrossRefQueryBuilder | None",
        kwargs.get("query_builder"),
    )
    if query_builder is None:
        query_builder = _create_default_crossref_query_builder(
            api_base=CROSSREF_API_BASE,
            mailto=mailto,
        )
    return query_builder


def _create_response_mapper(
    kwargs: dict[str, object],
) -> CrossRefResponseMapper:
    """Create response mapper with defaults."""
    response_mapper = cast(
        "CrossRefResponseMapper | None",
        kwargs.get("response_mapper"),
    )
    if response_mapper is None:
        response_mapper = _create_default_crossref_response_mapper()
    return response_mapper


def _create_batch_fetcher(
    kwargs: dict[str, object],
    http_client: UnifiedHTTPClient,
    logger: LoggerPort,
    adapter_metrics: AdapterMetricsRecorder,
    mailto: str,
    headers_fn: Callable[[], dict[str, str]],
    request_collector: APIRequestCollector,
) -> DoiBatchProcessor:
    """Create batch fetcher with defaults."""
    batch_fetcher = cast("DoiBatchProcessor | None", kwargs.get("batch_fetcher"))
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
    kwargs: dict[str, object],
    http_client: UnifiedHTTPClient,
    logger: LoggerPort,
    adapter_metrics: AdapterMetricsRecorder,
    mailto: str,
    headers_fn: Callable[[], dict[str, str]],
    request_collector: APIRequestCollector,
) -> SearchPaginator:
    """Create search paginator with defaults."""
    search_paginator = cast("SearchPaginator | None", kwargs.get("search_paginator"))
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
    kwargs: dict[str, object],
    logger: LoggerPort,
    search_fn: Callable[[str, int], AsyncIterator[JsonDict]],
) -> CrossRefTitleFallbackHandler:
    """Create title fallback handler with defaults."""
    title_fallback_handler = cast(
        "CrossRefTitleFallbackHandler | None",
        kwargs.get("title_fallback_handler"),
    )
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
    **kwargs: object,
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
    http_client_resolved, logger_resolved = _require_dependencies(http_client, logger)

    # Create helper services
    metrics = cast("MetricsPort | None", kwargs.get("metrics"))
    helper_services = _create_helper_services(logger_resolved, metrics)

    # Resolve optional components
    (
        error_handler,
        adapter_metrics,
        request_collector,
        fallback_fetch_service,
    ) = _resolve_optional_components(kwargs, helper_services)

    # Create query builder and get headers function
    query_builder = _create_query_builder(kwargs, mailto)
    headers_fn = query_builder.build_headers

    # Create response mapper
    response_mapper = _create_response_mapper(kwargs)

    # Create batch fetcher
    batch_fetcher = _create_batch_fetcher(
        kwargs,
        http_client_resolved,
        logger_resolved,
        adapter_metrics,
        mailto,
        headers_fn,
        request_collector,
    )

    # Create search paginator
    search_paginator = _create_search_paginator(
        kwargs,
        http_client_resolved,
        logger_resolved,
        adapter_metrics,
        mailto,
        headers_fn,
        request_collector,
    )

    # Create title fallback handler
    title_fallback_handler = _create_title_fallback_handler(
        kwargs,
        logger_resolved,
        search_paginator.search,
    )
    batch_size = cast(int, kwargs.get("batch_size", 50))
    dependency_context = cast("HttpAdapterDependencyContext | None", kwargs.get("dependency_context"))
    fetch_flow = cast("CrossRefFetchFlow | None", kwargs.get("fetch_flow"))

    return CrossRefAdapter(
        http_client=http_client_resolved,
        logger=logger_resolved,
        mailto=mailto,
        batch_size=batch_size,
        metrics=metrics,
        dependency_context=dependency_context,
        error_handler=error_handler,
        adapter_metrics=adapter_metrics,
        request_collector=request_collector,
        fallback_fetch_service=fallback_fetch_service,
        query_builder=query_builder,
        response_mapper=response_mapper,
        batch_fetcher=batch_fetcher,
        search_paginator=search_paginator,
        title_fallback_handler=title_fallback_handler,
        fetch_flow=fetch_flow,
    )
