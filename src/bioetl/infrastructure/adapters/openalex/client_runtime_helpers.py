"""Runtime assembly helpers for the OpenAlex adapter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common import FallbackFetchOrchestratorService
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.openalex.cursor_flow import (
    OpenAlexCursorFlowService,
)
from bioetl.infrastructure.adapters.openalex.fallback import (
    OpenAlexTitleFallbackHandler,
)
from bioetl.infrastructure.adapters.openalex.fallback_orchestrator import (
    OpenAlexFallbackOrchestrator,
)
from bioetl.infrastructure.adapters.openalex.query_execution import (
    OpenAlexQueryExecutor,
)
from bioetl.infrastructure.adapters.openalex.response_mapping import (
    OpenAlexResponseMapper,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings


__all__ = [
    "OpenAlexRuntimeServices",
    "build_openalex_runtime_services",
]

HeadersProvider = Callable[[], dict[str, str]]
NormalizeDoiFn = Callable[[str], str | None]
EscapeTitleForSearchFn = Callable[[str], str]
SearchByTitleFn = Callable[[str, int], Awaitable[list[BronzeRecord]]]
ExtractRecordIdFn = Callable[[BronzeRecord], str | None]


@dataclass(frozen=True, slots=True)
class OpenAlexRuntimeServices:
    """Resolved OpenAlex runtime collaborators after default/injected wiring."""

    fallback_fetch_service: FallbackFetchOrchestratorService
    query_executor: OpenAlexQueryExecutor
    response_mapper: OpenAlexResponseMapper
    cursor_flow: OpenAlexCursorFlowService
    fallback_handler: OpenAlexTitleFallbackHandler
    fallback_orchestrator: OpenAlexFallbackOrchestrator


def _create_default_openalex_query_executor(
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


def _create_default_openalex_response_mapper() -> OpenAlexResponseMapper:
    """Create the default OpenAlex response mapper."""
    return OpenAlexResponseMapper()


def _create_default_openalex_cursor_flow(
    *,
    mailto: str,
    batch_size: int,
    title_search_cache_size: int,
    normalize_doi: NormalizeDoiFn,
    escape_title_for_search: EscapeTitleForSearchFn,
    query_executor: OpenAlexQueryExecutor,
    response_mapper: OpenAlexResponseMapper,
    logger: LoggerPort,
    runtime_errors: tuple[type[Exception], ...],
) -> OpenAlexCursorFlowService:
    """Create the default OpenAlex cursor flow service."""
    return OpenAlexCursorFlowService(
        mailto=mailto,
        batch_size=batch_size,
        title_search_cache_size=title_search_cache_size,
        normalize_doi=normalize_doi,
        escape_title_for_search=escape_title_for_search,
        query_executor=query_executor,
        response_mapper=response_mapper,
        logger=logger,
        runtime_errors=runtime_errors,
    )


def _create_default_openalex_title_fallback_handler(
    *,
    logger: LoggerPort,
    search_fn: SearchByTitleFn,
) -> OpenAlexTitleFallbackHandler:
    """Create the default title fallback handler."""
    return OpenAlexTitleFallbackHandler(logger=logger, search_fn=search_fn)


def _create_default_openalex_fallback_orchestrator(
    *,
    fallback_fetch_service: FallbackFetchOrchestratorService,
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


def build_openalex_runtime_services(
    *,
    fallback_fetch_service: FallbackFetchOrchestratorService,
    openalex_query_executor: OpenAlexQueryExecutor | None,
    openalex_response_mapper: OpenAlexResponseMapper | None,
    openalex_cursor_flow: OpenAlexCursorFlowService | None,
    title_fallback_handler: OpenAlexTitleFallbackHandler | None,
    openalex_fallback_orchestrator: OpenAlexFallbackOrchestrator | None,
    http_client: UnifiedHTTPClient,
    adapter_metrics: AdapterMetricsRecorder,
    request_collector: APIRequestCollector,
    headers_provider: HeadersProvider,
    api_base: str,
    mailto: str,
    batch_size: int,
    title_search_cache_size: int,
    normalize_doi: NormalizeDoiFn,
    escape_title_for_search: EscapeTitleForSearchFn,
    extract_record_id: ExtractRecordIdFn,
    search_by_title: SearchByTitleFn,
    logger: LoggerPort,
    runtime_errors: tuple[type[Exception], ...],
) -> OpenAlexRuntimeServices:
    """Resolve OpenAlex runtime collaborators using injected overrides or defaults."""
    query_executor = (
        openalex_query_executor
        if openalex_query_executor is not None
        else _create_default_openalex_query_executor(
            http_client=http_client,
            adapter_metrics=adapter_metrics,
            request_collector=request_collector,
            headers_provider=headers_provider,
            api_base=api_base,
        )
    )
    response_mapper = (
        openalex_response_mapper
        if openalex_response_mapper is not None
        else _create_default_openalex_response_mapper()
    )
    cursor_flow = (
        openalex_cursor_flow
        if openalex_cursor_flow is not None
        else _create_default_openalex_cursor_flow(
            mailto=mailto,
            batch_size=batch_size,
            title_search_cache_size=title_search_cache_size,
            normalize_doi=normalize_doi,
            escape_title_for_search=escape_title_for_search,
            query_executor=query_executor,
            response_mapper=response_mapper,
            logger=logger,
            runtime_errors=runtime_errors,
        )
    )
    fallback_handler = (
        title_fallback_handler
        if title_fallback_handler is not None
        else _create_default_openalex_title_fallback_handler(
            logger=logger,
            search_fn=search_by_title,
        )
    )
    fallback_orchestrator = (
        openalex_fallback_orchestrator
        if openalex_fallback_orchestrator is not None
        else _create_default_openalex_fallback_orchestrator(
            fallback_fetch_service=fallback_fetch_service,
            fallback_handler=fallback_handler,
            normalize_id=normalize_doi,
            extract_record_id=extract_record_id,
            logger=logger,
        )
    )
    return OpenAlexRuntimeServices(
        fallback_fetch_service=fallback_fetch_service,
        query_executor=query_executor,
        response_mapper=response_mapper,
        cursor_flow=cursor_flow,
        fallback_handler=fallback_handler,
        fallback_orchestrator=fallback_orchestrator,
    )


# ============================================================================
# New Request-Style API (Phase 1: Basic Infrastructure)
# ============================================================================

@dataclass(frozen=True)
class OpenAlexRuntimeServicesRequest:
    """Request object for OpenAlex runtime services (new API).

    Phase 1: Basic infrastructure for request-style wiring.
    Centralizes core dependencies needed for OpenAlex adapter.
    """
    settings: Settings | None
    http_client: UnifiedHTTPClient
    tracer: TracingPort | None
    metrics: MetricsPort
    logger: LoggerPort


@dataclass(frozen=True)
class OpenAlexRuntimeServicesBundle:
    """Bundle of OpenAlex runtime services (new API).

    Phase 1: Basic bundle with core services only.
    Contains essential services needed for OpenAlex adapter operation.
    """
    http_client: UnifiedHTTPClient
    tracer: TracingPort | None
    metrics: MetricsPort
    logger: LoggerPort


def build_openalex_runtime_services_from_request(
    request: OpenAlexRuntimeServicesRequest,
) -> OpenAlexRuntimeServicesBundle:
    """Build OpenAlex runtime services bundle from request (new API).

    Phase 1: Basic implementation that validates and returns core services.
    This is the foundation for future refactoring.
    """
    # Validate request
    if not request.http_client:
        raise ValueError("HTTP client is required")
    if not request.metrics:
        raise ValueError("Metrics port is required")
    if not request.logger:
        raise ValueError("Logger is required")

    # Build and return bundle
    return OpenAlexRuntimeServicesBundle(
        http_client=request.http_client,
        tracer=request.tracer,
        metrics=request.metrics,
        logger=request.logger,
    )


# Update __all__ to include new API
__all__ = [
    "OpenAlexRuntimeServices",
    "OpenAlexRuntimeServicesBundle",
    "OpenAlexRuntimeServicesRequest",
    "build_openalex_runtime_services",
    "build_openalex_runtime_services_from_request",
]
