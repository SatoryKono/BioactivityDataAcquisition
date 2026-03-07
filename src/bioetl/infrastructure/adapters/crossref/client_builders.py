"""Default component builders for `CrossRefAdapter`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.adapters.common import ComposableFallbackDecorator
from bioetl.infrastructure.adapters.crossref.batch import (
    DoiBatchProcessor,
    SearchPaginator,
)
from bioetl.infrastructure.adapters.crossref.fallback import TitleFallbackHandler
from bioetl.infrastructure.adapters.crossref.fetch_flow import CrossRefFetchFlow
from bioetl.infrastructure.adapters.crossref.query_builder import CrossRefQueryBuilder
from bioetl.infrastructure.adapters.crossref.response_mapper import (
    CrossRefResponseMapper,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import JsonDict
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


def _create_default_crossref_query_builder(
    *, api_base: str, mailto: str
) -> CrossRefQueryBuilder:
    """Create default query builder for non-DI call sites."""
    return CrossRefQueryBuilder(api_base=api_base, mailto=mailto)


def _create_default_crossref_response_mapper() -> CrossRefResponseMapper:
    """Create default response mapper for non-DI call sites."""
    return CrossRefResponseMapper()


def _create_default_crossref_batch_fetcher(
    *,
    http: UnifiedHTTPClient,
    logger: LoggerPort,
    metrics: AdapterMetrics,
    mailto: str,
    api_base: str,
    headers_fn: Callable[[], dict[str, str]],
    request_collector: APIRequestCollector,
) -> DoiBatchProcessor:
    """Create default DOI batch processor for non-DI call sites."""
    return DoiBatchProcessor(
        http=http,
        logger=logger,
        metrics=metrics,
        mailto=mailto,
        api_base=api_base,
        headers_fn=headers_fn,
        request_collector=request_collector,
    )


def _create_default_crossref_search_paginator(
    *,
    http: UnifiedHTTPClient,
    logger: LoggerPort,
    metrics: AdapterMetrics,
    mailto: str,
    api_base: str,
    headers_fn: Callable[[], dict[str, str]],
    request_collector: APIRequestCollector,
) -> SearchPaginator:
    """Create default search paginator for non-DI call sites."""
    return SearchPaginator(
        http=http,
        logger=logger,
        metrics=metrics,
        mailto=mailto,
        api_base=api_base,
        headers_fn=headers_fn,
        request_collector=request_collector,
    )


def _create_default_crossref_title_fallback_handler(
    *, logger: LoggerPort, search_fn: Callable[[str, int], AsyncIterator[JsonDict]]
) -> TitleFallbackHandler:
    """Create default title fallback handler for non-DI call sites."""
    return TitleFallbackHandler(logger=logger, search_fn=search_fn)


def _create_default_crossref_fetch_flow(
    *,
    logger: LoggerPort,
    batch_fetcher: DoiBatchProcessor,
    search_paginator: SearchPaginator,
    fallback_decorator: ComposableFallbackDecorator,
    batch_size: int,
    response_mapper: CrossRefResponseMapper,
) -> CrossRefFetchFlow:
    """Create default fetch flow for non-DI call sites."""
    return CrossRefFetchFlow(
        logger=logger,
        batch_fetcher=batch_fetcher,
        search_paginator=search_paginator,
        fallback_decorator=fallback_decorator,
        batch_size=batch_size,
        response_mapper=response_mapper,
    )


__all__ = [
    "_create_default_crossref_batch_fetcher",
    "_create_default_crossref_fetch_flow",
    "_create_default_crossref_query_builder",
    "_create_default_crossref_response_mapper",
    "_create_default_crossref_search_paginator",
    "_create_default_crossref_title_fallback_handler",
]
