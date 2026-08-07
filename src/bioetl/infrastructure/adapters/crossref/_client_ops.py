"""Fetch/health/metadata operations for CrossRefAdapter facade."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, cast

from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.types import BronzeRecord, HealthStatus
from bioetl.infrastructure.adapters.crossref.client_observability_helpers import (
    build_crossref_source_metadata,
    clear_crossref_request_collector,
    get_crossref_request_count,
    probe_crossref_health,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.crossref.fetch_flow import CrossRefFetchFlow
    from bioetl.infrastructure.adapters.crossref.query_builder import (
        CrossRefQueryPlanner,
    )
    from bioetl.infrastructure.adapters.crossref.response_mapper import (
        CrossRefResponseMapper,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

__all__ = [
    "crossref_clear_request_collector",
    "crossref_fetch",
    "crossref_fetch_filtered",
    "crossref_fetch_filtered_with_fallback",
    "crossref_probe_health",
    "crossref_request_count",
    "crossref_source_metadata",
]


async def crossref_fetch_filtered(
    *,
    flow: CrossRefFetchFlow,
    entity_type: str,
    filter_ids: list[str],
    filter_field: str,
    limit: int | None,
) -> AsyncIterator[BronzeRecord]:
    """Fetch CrossRef publications by DOI list (FilterableDataSourcePort)."""
    async for publication in flow.fetch_filtered(
        entity_type=entity_type,
        filter_ids=filter_ids,
        filter_field=filter_field,
        limit=limit,
    ):
        yield publication


async def crossref_fetch_filtered_with_fallback(
    *,
    flow: CrossRefFetchFlow,
    entity_type: str,
    filter_ids: list[str],
    filter_field: str,
    fallback_mapping: dict[str, str],
    limit: int | None,
) -> AsyncIterator[BronzeRecord]:
    """Fetch publications by DOI with title-search fallback for misses."""
    async for publication in flow.fetch_filtered_with_fallback(
        entity_type=entity_type,
        filter_ids=filter_ids,
        filter_field=filter_field,
        fallback_mapping=fallback_mapping,
        limit=limit,
    ):
        yield publication


async def crossref_fetch(
    *,
    flow: CrossRefFetchFlow,
    entity_type: str,
    limit: int | None,
    query: str | None,
    filter_ids: list[str] | None,
    filter_field: str | None,
) -> AsyncIterator[BronzeRecord]:
    """Fetch CrossRef publications via DOI filters or free-text query."""
    async for publication in flow.fetch(
        entity_type=entity_type,
        limit=limit,
        query=query,
        filter_ids=filter_ids,
        filter_field=filter_field,
    ):
        yield publication


async def crossref_probe_health(
    *,
    http_client: UnifiedHTTPClient,
    query_builder: CrossRefQueryPlanner,
    response_mapper: CrossRefResponseMapper,
    adapter_metrics: AdapterMetricsRecorder,
    headers_provider: Callable[[], dict[str, str]],
    logger: LoggerPort,
    health_errors: tuple[type[Exception], ...],
) -> HealthStatus:
    """Probe CrossRef API health with response-status classification."""
    return await probe_crossref_health(
        http_client=http_client,
        query_builder=query_builder,
        response_mapper=response_mapper,
        adapter_metrics=adapter_metrics,
        headers_provider=headers_provider,
        logger=logger,
        health_errors=health_errors,
    )


def crossref_source_metadata(
    *,
    request_collector: APIRequestCollector | None,
    api_base: str,
    api_version: str | None,
) -> SourceMetadata:
    """Return and clear aggregated API request metadata."""
    return build_crossref_source_metadata(
        request_collector=cast("APIRequestCollector", request_collector),
        api_base=api_base,
        api_version=api_version,
    )


def crossref_clear_request_collector(
    *,
    request_collector: APIRequestCollector | None,
) -> None:
    """Clear the collector without returning metadata."""
    clear_crossref_request_collector(
        request_collector=cast("APIRequestCollector", request_collector)
    )


def crossref_request_count(
    *,
    request_collector: APIRequestCollector | None,
) -> int:
    """Number of recorded API requests since last clear."""
    return get_crossref_request_count(
        request_collector=cast("APIRequestCollector", request_collector)
    )
