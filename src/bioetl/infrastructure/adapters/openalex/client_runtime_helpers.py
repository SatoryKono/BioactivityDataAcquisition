# OpenAlex payload fields are object-typed at boundary (PD2-6).
"""Runtime assembly helpers for the OpenAlex adapter."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.infrastructure.adapters.common import FallbackFetchOrchestrator
from bioetl.infrastructure.adapters.openalex._client_runtime_factories import (
    create_default_openalex_cursor_flow as _create_default_openalex_cursor_flow,
    create_default_openalex_fallback_orchestrator as _create_default_openalex_fallback_orchestrator,
    create_default_openalex_query_executor as _create_default_openalex_query_executor,
    create_default_openalex_response_mapper as _create_default_openalex_response_mapper,
    create_default_openalex_title_fallback_handler as _create_default_openalex_title_fallback_handler,
)
from bioetl.infrastructure.adapters.openalex._client_runtime_request import (
    OpenAlexRuntimeServicesRequest,
    coerce_openalex_runtime_services_request as _coerce_openalex_runtime_services_request,
)
from bioetl.infrastructure.adapters.openalex.cursor_flow import OpenAlexCursorFlow
from bioetl.infrastructure.adapters.openalex.fallback import OpenAlexTitleFallbackHandler
from bioetl.infrastructure.adapters.openalex.fallback_orchestrator import (
    OpenAlexFallbackOrchestrator,
)
from bioetl.infrastructure.adapters.openalex.query_execution import OpenAlexQueryExecutor
from bioetl.infrastructure.adapters.openalex.response_mapping import (
    OpenAlexResponseMapper,
)

__all__ = [
    "OpenAlexRuntimeServices",
    "OpenAlexRuntimeServicesRequest",
    "build_openalex_runtime_services",
    "build_openalex_runtime_services_from_request",
]


@dataclass(frozen=True, slots=True)
class OpenAlexRuntimeServices:
    """Resolved OpenAlex runtime collaborators after default/injected wiring."""

    fallback_fetch_service: FallbackFetchOrchestrator
    query_executor: OpenAlexQueryExecutor
    response_mapper: OpenAlexResponseMapper
    cursor_flow: OpenAlexCursorFlow
    fallback_handler: OpenAlexTitleFallbackHandler
    fallback_orchestrator: OpenAlexFallbackOrchestrator


def build_openalex_runtime_services(
    request: OpenAlexRuntimeServicesRequest | None = None,
    /,
    **kwargs: object,
) -> OpenAlexRuntimeServices:
    """Resolve OpenAlex runtime collaborators using injected overrides or defaults."""
    resolved = _coerce_openalex_runtime_services_request(request, **kwargs)
    query_executor = (
        resolved.openalex_query_executor
        if resolved.openalex_query_executor is not None
        else _create_default_openalex_query_executor(
            http_client=resolved.http_client,
            adapter_metrics=resolved.adapter_metrics,
            request_collector=resolved.request_collector,
            headers_provider=resolved.headers_provider,
            api_base=resolved.api_base,
        )
    )
    response_mapper = (
        resolved.openalex_response_mapper
        if resolved.openalex_response_mapper is not None
        else _create_default_openalex_response_mapper()
    )
    cursor_flow = (
        resolved.openalex_cursor_flow
        if resolved.openalex_cursor_flow is not None
        else _create_default_openalex_cursor_flow(
            mailto=resolved.mailto,
            api_key=resolved.api_key,
            batch_size=resolved.batch_size,
            title_search_cache_size=resolved.title_search_cache_size,
            normalize_doi=resolved.normalize_doi,
            escape_title_for_search=resolved.escape_title_for_search,
            query_executor=query_executor,
            response_mapper=response_mapper,
            logger=resolved.logger,
            runtime_errors=resolved.runtime_errors,
        )
    )
    fallback_handler = (
        resolved.title_fallback_handler
        if resolved.title_fallback_handler is not None
        else _create_default_openalex_title_fallback_handler(
            logger=resolved.logger,
            search_fn=resolved.search_by_title,
        )
    )
    fallback_orchestrator = (
        resolved.openalex_fallback_orchestrator
        if resolved.openalex_fallback_orchestrator is not None
        else _create_default_openalex_fallback_orchestrator(
            fallback_fetch_service=resolved.fallback_fetch_service,
            fallback_handler=fallback_handler,
            normalize_id=resolved.normalize_doi,
            extract_record_id=resolved.extract_record_id,
            logger=resolved.logger,
        )
    )
    return OpenAlexRuntimeServices(
        fallback_fetch_service=resolved.fallback_fetch_service,
        query_executor=query_executor,
        response_mapper=response_mapper,
        cursor_flow=cursor_flow,
        fallback_handler=fallback_handler,
        fallback_orchestrator=fallback_orchestrator,
    )


def build_openalex_runtime_services_from_request(
    request: OpenAlexRuntimeServicesRequest,
) -> OpenAlexRuntimeServices:
    """Request-style alias for OpenAlex runtime collaborator assembly."""
    return build_openalex_runtime_services(request)
