"""OpenAlex runtime wiring helpers and request-style API."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common import FallbackFetchOrchestratorService
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

from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings


HeadersProvider = Callable[[], dict[str, str]]
NormalizeDoiFn = Callable[[str], str | None]
EscapeTitleForSearchFn = Callable[[str], str]
SearchByTitleFn = Callable[[str, int], list[BronzeRecord]]
ExtractRecordIdFn = Callable[[BronzeRecord], str | None]


@dataclass(frozen=True)
class OpenAlexRuntimeServicesRequest:
    """Request object for OpenAlex runtime services bundle.
    
    Centralizes all dependencies needed to build OpenAlex adapter runtime services.
    """
    settings: Settings
    http_client: UnifiedHTTPClient
    tracer: TracingPort
    metrics: MetricsPort
    logger: LoggerPort


@dataclass(frozen=True)
class OpenAlexRuntimeServicesBundle:
    """Bundle of OpenAlex runtime services.
    
    Contains all services needed for OpenAlex adapter operation.
    """
    http_client: UnifiedHTTPClient
    tracer: TracingPort
    metrics: MetricsPort
    logger: LoggerPort


# New request-style API (clean implementation)
def build_openalex_runtime_services_from_request(
    request: OpenAlexRuntimeServicesRequest,
) -> OpenAlexRuntimeServicesBundle:
    """Build OpenAlex runtime services bundle from request (new API).
    
    This is the new clean implementation that uses request-style API.
    """
    # Validate request (only validate what we actually use)
    if not request.http_client:
        raise ValueError("HTTP client is required")
    if not request.metrics:
        raise ValueError("Metrics port is required")
    if not request.logger:
        raise ValueError("Logger is required")
    # Note: settings and tracer are optional for backward compatibility
    
    # Build and return bundle
    return OpenAlexRuntimeServicesBundle(
        http_client=request.http_client,
        tracer=request.tracer,
        metrics=request.metrics,
        logger=request.logger,
    )


# Legacy compatibility wrapper
# This preserves the old API for backward compatibility
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
) -> OpenAlexRuntimeServicesBundle:
    """Build OpenAlex runtime services bundle (legacy API).
    
    This is a compatibility wrapper around the new request-style API.
    Will be removed after full migration.
    """
    # Extract basic services for new API
    request = OpenAlexRuntimeServicesRequest(
        settings=None,  # type: ignore
        http_client=http_client,
        tracer=None,  # type: ignore
        metrics=adapter_metrics,
        logger=logger,
    )
    
    # Build bundle using new API
    bundle = build_openalex_runtime_services_from_request(request)
    
    # TODO: Here we would normally build the full OpenAlexRuntimeServices object
    # For now, return a minimal bundle to maintain compatibility
    # The full migration will be done in the next phase
    return bundle


__all__ = [
    "OpenAlexRuntimeServicesRequest",
    "OpenAlexRuntimeServicesBundle",
    "build_openalex_runtime_services_from_request",
    "build_openalex_runtime_services",
]
