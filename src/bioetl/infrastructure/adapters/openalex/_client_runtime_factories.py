"""Default factory helpers for OpenAlex runtime collaborator assembly."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.openalex.cursor_flow import OpenAlexCursorFlow
from bioetl.infrastructure.adapters.openalex.fallback import OpenAlexTitleFallbackHandler
from bioetl.infrastructure.adapters.openalex.fallback_orchestrator import (
    OpenAlexFallbackOrchestrator,
)
from bioetl.infrastructure.adapters.openalex.query_execution import OpenAlexQueryExecutor
from bioetl.infrastructure.adapters.openalex.response_mapping import (
    OpenAlexResponseMapper,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.common import FallbackFetchOrchestrator
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

__all__ = [
    "create_default_openalex_cursor_flow",
    "create_default_openalex_fallback_orchestrator",
    "create_default_openalex_query_executor",
    "create_default_openalex_response_mapper",
    "create_default_openalex_title_fallback_handler",
]

HeadersProvider = Callable[[], dict[str, str]]
NormalizeDoiFn = Callable[[str], str | None]
EscapeTitleForSearchFn = Callable[[str], str]
SearchByTitleFn = Callable[[str, int], Awaitable[list[BronzeRecord]]]
ExtractRecordIdFn = Callable[[BronzeRecord], str | None]


def create_default_openalex_query_executor(
    *,
    http_client: UnifiedHTTPClient,
    adapter_metrics: AdapterMetricsRecorder,
    request_collector: APIRequestCollector,
    headers_provider: HeadersProvider,
    api_base: str,
) -> OpenAlexQueryExecutor:
    """Create the default OpenAlex query executor."""
    return OpenAlexQueryExecutor(
        http_client=http_client,
        adapter_metrics=adapter_metrics,
        request_collector=request_collector,
        headers_provider=headers_provider,
        api_base=api_base,
    )


def create_default_openalex_response_mapper() -> OpenAlexResponseMapper:
    """Create the default OpenAlex response mapper."""
    return OpenAlexResponseMapper()


def create_default_openalex_cursor_flow(
    *,
    mailto: str | None,
    api_key: str | None,
    batch_size: int,
    title_search_cache_size: int,
    normalize_doi: NormalizeDoiFn,
    escape_title_for_search: EscapeTitleForSearchFn,
    query_executor: OpenAlexQueryExecutor,
    response_mapper: OpenAlexResponseMapper,
    logger: LoggerPort,
    runtime_errors: tuple[type[Exception], ...],
) -> OpenAlexCursorFlow:
    """Create the default OpenAlex cursor flow."""
    return OpenAlexCursorFlow(
        mailto=mailto,
        api_key=api_key,
        batch_size=batch_size,
        title_search_cache_size=title_search_cache_size,
        normalize_doi=normalize_doi,
        escape_title_for_search=escape_title_for_search,
        query_executor=query_executor,
        response_mapper=response_mapper,
        logger=logger,
        runtime_errors=runtime_errors,
    )


def create_default_openalex_title_fallback_handler(
    *,
    logger: LoggerPort,
    search_fn: SearchByTitleFn,
) -> OpenAlexTitleFallbackHandler:
    """Create the default title fallback handler."""
    return OpenAlexTitleFallbackHandler(logger=logger, search_fn=search_fn)


def create_default_openalex_fallback_orchestrator(
    *,
    fallback_fetch_service: FallbackFetchOrchestrator,
    fallback_handler: OpenAlexTitleFallbackHandler,
    normalize_id: NormalizeDoiFn,
    extract_record_id: ExtractRecordIdFn,
    logger: LoggerPort,
) -> OpenAlexFallbackOrchestrator:
    """Create the default OpenAlex fallback orchestrator."""
    return OpenAlexFallbackOrchestrator(
        fallback_fetch_service=fallback_fetch_service,
        fallback_handler=fallback_handler,
        normalize_id=normalize_id,
        extract_record_id=extract_record_id,
        logger=logger,
    )
