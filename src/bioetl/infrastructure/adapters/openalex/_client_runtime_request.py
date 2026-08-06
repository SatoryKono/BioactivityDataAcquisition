"""Request coercion for OpenAlex runtime collaborator assembly."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.common import FallbackFetchOrchestrator
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.adapters.openalex.cursor_flow import OpenAlexCursorFlow
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

__all__ = [
    "OpenAlexRuntimeServicesRequest",
    "coerce_openalex_runtime_services_request",
]

HeadersProvider = Callable[[], dict[str, str]]
NormalizeDoiFn = Callable[[str], str | None]
EscapeTitleForSearchFn = Callable[[str], str]
SearchByTitleFn = Callable[[str, int], Awaitable[list[BronzeRecord]]]
ExtractRecordIdFn = Callable[[BronzeRecord], str | None]


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


def coerce_openalex_runtime_services_request(
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
        fallback_fetch_service=kwargs.pop("fallback_fetch_service"),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        openalex_query_executor=kwargs.pop("openalex_query_executor", None),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        openalex_response_mapper=kwargs.pop("openalex_response_mapper", None),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        openalex_cursor_flow=kwargs.pop("openalex_cursor_flow", None),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        title_fallback_handler=kwargs.pop("title_fallback_handler", None),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        openalex_fallback_orchestrator=kwargs.pop(  # pyright: ignore[reportArgumentType]
            "openalex_fallback_orchestrator", None
        ),  # type: ignore[arg-type]
        http_client=kwargs.pop("http_client"),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        adapter_metrics=kwargs.pop("adapter_metrics"),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        request_collector=kwargs.pop("request_collector"),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        headers_provider=kwargs.pop("headers_provider"),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        api_base=kwargs.pop("api_base"),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        mailto=kwargs.pop("mailto"),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        api_key=kwargs.pop("api_key", None),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        batch_size=kwargs.pop("batch_size"),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        title_search_cache_size=kwargs.pop("title_search_cache_size"),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        normalize_doi=kwargs.pop("normalize_doi"),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        escape_title_for_search=kwargs.pop("escape_title_for_search"),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        extract_record_id=kwargs.pop("extract_record_id"),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        search_by_title=kwargs.pop("search_by_title"),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        logger=kwargs.pop("logger"),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        runtime_errors=kwargs.pop("runtime_errors"),  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
    )
