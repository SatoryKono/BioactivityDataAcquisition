# pyright: reportArgumentType=false
# OpenAlex payload fields are object-typed at boundary (PD2-6).
"""Runtime assembly helpers for the OpenAlex adapter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common import FallbackFetchOrchestrator
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.openalex.cursor_flow import (
    OpenAlexCursorFlow,
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
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


__all__ = [
    "OpenAlexRuntimeServices",
    "OpenAlexRuntimeServicesRequest",
    "build_openalex_runtime_services",
    "build_openalex_runtime_services_from_request",
]

HeadersProvider = Callable[[], dict[str, str]]
NormalizeDoiFn = Callable[[str], str | None]
EscapeTitleForSearchFn = Callable[[str], str]
SearchByTitleFn = Callable[[str, int], Awaitable[list[BronzeRecord]]]
ExtractRecordIdFn = Callable[[BronzeRecord], str | None]


@dataclass(frozen=True, slots=True)
class OpenAlexRuntimeServices:
    """Resolved OpenAlex runtime collaborators after default/injected wiring."""

    fallback_fetch_service: FallbackFetchOrchestrator
    query_executor: OpenAlexQueryExecutor
    response_mapper: OpenAlexResponseMapper
    cursor_flow: OpenAlexCursorFlow
    fallback_handler: OpenAlexTitleFallbackHandler
    fallback_orchestrator: OpenAlexFallbackOrchestrator


@dataclass(frozen=True, slots=True)
class OpenAlexRuntimeServicesRequest:
    """Typed input for OpenAlex runtime collaborator assembly."""

    fallback_fetch_service: FallbackFetchOrchestrator
    openalex_query_executor: OpenAlexQueryExecutor | None
    openalex_response_mapper: OpenAlexResponseMapper | None
    openalex_cursor_flow: OpenAlexCursorFlow | None
    title_fallback_handler: OpenAlexTitleFallbackHandler | None
    openalex_fallback_orchestrator: OpenAlexFallbackOrchestrator | None
    http_client: UnifiedHTTPClient
    adapter_metrics: AdapterMetricsRecorder
    request_collector: APIRequestCollector
    headers_provider: HeadersProvider
    api_base: str
    mailto: str | None
    batch_size: int
    title_search_cache_size: int
    normalize_doi: NormalizeDoiFn
    escape_title_for_search: EscapeTitleForSearchFn
    extract_record_id: ExtractRecordIdFn
    search_by_title: SearchByTitleFn
    logger: LoggerPort
    runtime_errors: tuple[type[Exception], ...]
    api_key: str | None = None


def _coerce_openalex_runtime_services_request(
    request: OpenAlexRuntimeServicesRequest | None = None,
    /,
    **kwargs: object,
) -> OpenAlexRuntimeServicesRequest:
    """Normalize request-style and legacy kwargs runtime inputs."""
    if request is not None:
        if kwargs:
            unexpected_args = ", ".join(sorted(kwargs))
            raise TypeError(
                "build_openalex_runtime_services received unexpected keyword "
                f"arguments with request object: {unexpected_args}"
            )
        return request

    expected_keys = {
        "fallback_fetch_service",
        "openalex_query_executor",
        "openalex_response_mapper",
        "openalex_cursor_flow",
        "title_fallback_handler",
        "openalex_fallback_orchestrator",
        "http_client",
        "adapter_metrics",
        "request_collector",
        "headers_provider",
        "api_base",
        "mailto",
        "api_key",
        "batch_size",
        "title_search_cache_size",
        "normalize_doi",
        "escape_title_for_search",
        "extract_record_id",
        "search_by_title",
        "logger",
        "runtime_errors",
    }
    unexpected_keys = sorted(kwargs.keys() - expected_keys)
    if unexpected_keys:
        unexpected_args = ", ".join(unexpected_keys)
        raise TypeError(
            "build_openalex_runtime_services received unexpected keyword "
            f"arguments: {unexpected_args}"
        )

    return OpenAlexRuntimeServicesRequest(
        fallback_fetch_service=kwargs.pop("fallback_fetch_service"),  # type: ignore[arg-type]
        openalex_query_executor=kwargs.pop("openalex_query_executor", None),  # type: ignore[arg-type]
        openalex_response_mapper=kwargs.pop("openalex_response_mapper", None),  # type: ignore[arg-type]
        openalex_cursor_flow=kwargs.pop("openalex_cursor_flow", None),  # type: ignore[arg-type]
        title_fallback_handler=kwargs.pop("title_fallback_handler", None),  # type: ignore[arg-type]
        openalex_fallback_orchestrator=kwargs.pop(
            "openalex_fallback_orchestrator", None
        ),  # type: ignore[arg-type]
        http_client=kwargs.pop("http_client"),  # type: ignore[arg-type]
        adapter_metrics=kwargs.pop("adapter_metrics"),  # type: ignore[arg-type]
        request_collector=kwargs.pop("request_collector"),  # type: ignore[arg-type]
        headers_provider=kwargs.pop("headers_provider"),  # type: ignore[arg-type]
        api_base=kwargs.pop("api_base"),  # type: ignore[arg-type]
        mailto=kwargs.pop("mailto"),  # type: ignore[arg-type]
        api_key=kwargs.pop("api_key", None),  # type: ignore[arg-type]
        batch_size=kwargs.pop("batch_size"),  # type: ignore[arg-type]
        title_search_cache_size=kwargs.pop("title_search_cache_size"),  # type: ignore[arg-type]
        normalize_doi=kwargs.pop("normalize_doi"),  # type: ignore[arg-type]
        escape_title_for_search=kwargs.pop("escape_title_for_search"),  # type: ignore[arg-type]
        extract_record_id=kwargs.pop("extract_record_id"),  # type: ignore[arg-type]
        search_by_title=kwargs.pop("search_by_title"),  # type: ignore[arg-type]
        logger=kwargs.pop("logger"),  # type: ignore[arg-type]
        runtime_errors=kwargs.pop("runtime_errors"),  # type: ignore[arg-type]
    )


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


def _create_default_openalex_title_fallback_handler(
    *,
    logger: LoggerPort,
    search_fn: SearchByTitleFn,
) -> OpenAlexTitleFallbackHandler:
    """Create the default title fallback handler."""
    return OpenAlexTitleFallbackHandler(logger=logger, search_fn=search_fn)


def _create_default_openalex_fallback_orchestrator(
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
