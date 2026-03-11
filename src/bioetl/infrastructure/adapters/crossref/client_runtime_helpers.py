"""Runtime assembly helpers for the CrossRef adapter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.infrastructure.adapters.common import ComposableFallbackDecorator
from bioetl.infrastructure.adapters.crossref.batch import (
    DoiBatchProcessor,
    SearchPaginatorHelper,
)
from bioetl.infrastructure.adapters.crossref.client_builders import (
    _create_default_crossref_batch_fetcher,
    _create_default_crossref_fetch_flow,
    _create_default_crossref_query_builder,
    _create_default_crossref_response_mapper,
    _create_default_crossref_search_paginator,
    _create_default_crossref_title_fallback_handler,
)
from bioetl.infrastructure.adapters.crossref.fallback import TitleFallbackHandler
from bioetl.infrastructure.adapters.crossref.fetch_flow import CrossRefFetchFlow
from bioetl.infrastructure.adapters.crossref.query_builder import CrossRefQueryBuilder
from bioetl.infrastructure.adapters.crossref.response_mapper import (
    CrossRefResponseMapper,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


__all__ = [
    "CrossRefRuntimeServices",
    "build_crossref_fetch_flow",
    "build_crossref_runtime_services",
]


@dataclass(frozen=True, slots=True)
class CrossRefRuntimeServices:
    """Resolved CrossRef runtime collaborators after default/injected wiring."""

    query_builder: CrossRefQueryBuilder
    response_mapper: CrossRefResponseMapper
    batch_fetcher: DoiBatchProcessor
    search_paginator: SearchPaginatorHelper
    fallback_handler: TitleFallbackHandler


def build_crossref_runtime_services(
    *,
    query_builder: CrossRefQueryBuilder | None,
    response_mapper: CrossRefResponseMapper | None,
    batch_fetcher: DoiBatchProcessor | None,
    search_paginator: SearchPaginatorHelper | None,
    title_fallback_handler: TitleFallbackHandler | None,
    http_client: UnifiedHTTPClient,
    logger: LoggerPort,
    adapter_metrics: AdapterMetricsRecorder,
    request_collector: APIRequestCollector,
    mailto: str,
    api_base: str,
    headers_fn: Callable[[], dict[str, str]],
) -> CrossRefRuntimeServices:
    """Resolve CrossRef runtime collaborators using injected overrides or defaults."""
    resolved_query_builder = (
        query_builder
        if query_builder is not None
        else _create_default_crossref_query_builder(
            api_base=api_base,
            mailto=mailto,
        )
    )
    resolved_response_mapper = (
        response_mapper
        if response_mapper is not None
        else _create_default_crossref_response_mapper()
    )
    resolved_batch_fetcher = (
        batch_fetcher
        if batch_fetcher is not None
        else _create_default_crossref_batch_fetcher(
            http=http_client,
            logger=logger,
            metrics=adapter_metrics,
            mailto=mailto,
            api_base=api_base,
            headers_fn=headers_fn,
            request_collector=request_collector,
        )
    )
    resolved_search_paginator = (
        search_paginator
        if search_paginator is not None
        else _create_default_crossref_search_paginator(
            http=http_client,
            logger=logger,
            metrics=adapter_metrics,
            mailto=mailto,
            api_base=api_base,
            headers_fn=headers_fn,
            request_collector=request_collector,
        )
    )
    resolved_fallback_handler = (
        title_fallback_handler
        if title_fallback_handler is not None
        else _create_default_crossref_title_fallback_handler(
            logger=logger,
            search_fn=resolved_search_paginator.search,
        )
    )
    return CrossRefRuntimeServices(
        query_builder=resolved_query_builder,
        response_mapper=resolved_response_mapper,
        batch_fetcher=resolved_batch_fetcher,
        search_paginator=resolved_search_paginator,
        fallback_handler=resolved_fallback_handler,
    )


def build_crossref_fetch_flow(
    *,
    fetch_flow: CrossRefFetchFlow | None,
    logger: LoggerPort,
    batch_fetcher: DoiBatchProcessor,
    search_paginator: SearchPaginatorHelper,
    fallback_decorator: ComposableFallbackDecorator,
    batch_size: int,
    response_mapper: CrossRefResponseMapper,
) -> CrossRefFetchFlow:
    """Resolve CrossRef fetch flow using injected override or default builder."""
    if fetch_flow is not None:
        return fetch_flow
    return _create_default_crossref_fetch_flow(
        logger=logger,
        batch_fetcher=batch_fetcher,
        search_paginator=search_paginator,
        fallback_decorator=fallback_decorator,
        batch_size=batch_size,
        response_mapper=response_mapper,
    )
