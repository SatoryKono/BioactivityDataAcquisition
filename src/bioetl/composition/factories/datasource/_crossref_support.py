from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import cast

from bioetl.composition.factories.datasource._crossref_inputs import resolve_mailto
from bioetl.composition.factories.datasource.adapter_helpers import (
    AdapterHelperServices,
    AdapterHelpersFactory,
)
from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common import FallbackFetchOrchestratorService
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.crossref import CROSSREF_API_BASE
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
from bioetl.infrastructure.adapters.crossref.types import (
    CrossRefBatchFetcher,
    CrossRefSearchPaginator,
)
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.config import Settings


@dataclass(frozen=True)
class CrossRefAdapterComponents:
    metrics: MetricsPort | None
    error_handler: ErrorHandlerPort
    adapter_metrics: AdapterMetricsRecorder
    request_collector: APIRequestCollector
    fallback_fetch_service: FallbackFetchOrchestratorService
    query_builder: CrossRefQueryBuilder
    response_mapper: CrossRefResponseMapper
    batch_fetcher: CrossRefBatchFetcher
    search_paginator: CrossRefSearchPaginator
    title_fallback_handler: CrossRefTitleFallbackHandler


def _create_helper_services(
    logger: LoggerPort, metrics: MetricsPort | None
) -> AdapterHelperServices:
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


def _create_response_mapper(kwargs: dict[str, object]) -> CrossRefResponseMapper:
    response_mapper = cast(
        "CrossRefResponseMapper | None", kwargs.get("response_mapper")
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
) -> CrossRefBatchFetcher:
    batch_fetcher = cast("CrossRefBatchFetcher | None", kwargs.get("batch_fetcher"))
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
) -> CrossRefSearchPaginator:
    search_paginator = cast(
        "CrossRefSearchPaginator | None",
        kwargs.get("search_paginator"),
    )
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
    title_fallback_handler = cast(
        "CrossRefTitleFallbackHandler | None", kwargs.get("title_fallback_handler")
    )
    if title_fallback_handler is None:
        title_fallback_handler = _create_default_crossref_title_fallback_handler(
            logger=logger,
            search_fn=search_fn,
        )
    return title_fallback_handler


def build_crossref_components(
    *,
    kwargs: dict[str, object],
    http_client: UnifiedHTTPClient,
    logger: LoggerPort,
    settings: Settings | None,
) -> CrossRefAdapterComponents:
    mailto = resolve_mailto(kwargs, settings)
    metrics = cast("MetricsPort | None", kwargs.get("metrics"))
    helper_services = _create_helper_services(logger, metrics)
    error_handler, adapter_metrics, request_collector, fallback_fetch_service = (
        _resolve_optional_components(kwargs, helper_services)
    )
    query_builder = _create_query_builder(kwargs, mailto)
    headers_fn = query_builder.build_headers
    response_mapper = _create_response_mapper(kwargs)
    search_paginator = _create_search_paginator(
        kwargs,
        http_client,
        logger,
        adapter_metrics,
        mailto,
        headers_fn,
        request_collector,
    )
    return CrossRefAdapterComponents(
        metrics=metrics,
        error_handler=error_handler,
        adapter_metrics=adapter_metrics,
        request_collector=request_collector,
        fallback_fetch_service=fallback_fetch_service,
        query_builder=query_builder,
        response_mapper=response_mapper,
        batch_fetcher=_create_batch_fetcher(
            kwargs,
            http_client,
            logger,
            adapter_metrics,
            mailto,
            headers_fn,
            request_collector,
        ),
        search_paginator=search_paginator,
        title_fallback_handler=_create_title_fallback_handler(
            kwargs,
            logger,
            search_paginator.search,
        ),
    )
