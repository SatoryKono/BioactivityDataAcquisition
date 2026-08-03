"""Internal flow helpers for OpenAlex filter and fallback fetch paths."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.openalex._filter_fetch_requests import (
    _FallbackFetchRequest,
    _FetchRequest,
    _FilteredFetchRequest,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.openalex.fallback_orchestrator import (
        OpenAlexFallbackOrchestrator,
    )

_FilteredRecordFetcher = Callable[[list[str], int | None], AsyncIterator[BronzeRecord]]


class _OpenAlexFilterFetchHost(Protocol):
    """Minimal host contract required by OpenAlex filter-flow helpers."""

    _logger: LoggerPort
    _fallback_orchestrator: OpenAlexFallbackOrchestrator

    def _validate_entity_type(self, entity_type: str) -> None: ...

    def _fetch_filtered_by_doi(
        self,
        filter_ids: list[str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]: ...

    def _fetch_filtered_by_title(
        self,
        titles: list[str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]: ...

    def _batch_doi_lookup(
        self,
        valid_dois: list[str],
        limit: int | None,
        start_count: int = 0,
    ) -> AsyncIterator[BronzeRecord]: ...

    def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]: ...

    def _fetch_by_query(
        self,
        *,
        query: str,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]: ...


def resolve_filtered_record_fetcher(
    host: _OpenAlexFilterFetchHost,
    filter_field: str,
) -> _FilteredRecordFetcher | None:
    """Resolve one supported filtered fetcher or log and skip."""
    if filter_field == "doi":
        return host._fetch_filtered_by_doi
    if filter_field == "title":
        return host._fetch_filtered_by_title
    host._logger.warning(
        "unsupported_filter_field",
        field=filter_field,
        msg="OpenAlex only supports 'doi' or 'title' filtering, skipping",
    )
    return None


def build_primary_record_fetcher(
    host: _OpenAlexFilterFetchHost,
) -> _FilteredRecordFetcher:
    """Build the DOI-first primary fetcher for fallback orchestration."""

    def _primary_records(
        primary_ids: list[str],
        request_limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        return host._batch_doi_lookup(primary_ids, request_limit)

    return _primary_records


async def iterate_filtered_request(
    host: _OpenAlexFilterFetchHost,
    request: _FilteredFetchRequest,
) -> AsyncIterator[BronzeRecord]:
    """Execute one normalized filtered request."""
    fetcher = resolve_filtered_record_fetcher(host, request.filter_field)
    if fetcher is None:
        return
    async for work in fetcher(request.filter_ids, request.limit):
        yield work


async def iterate_fallback_request(
    host: _OpenAlexFilterFetchHost,
    request: _FallbackFetchRequest,
) -> AsyncIterator[BronzeRecord]:
    """Execute one normalized fallback request."""
    async for work in host._fallback_orchestrator.execute(
        filter_ids=request.filter_ids,
        fallback_mapping=request.fallback_mapping,
        primary_record_fetcher=build_primary_record_fetcher(host),
        limit=request.limit,
        filter_field=request.filter_field,
    ):
        yield work


async def iterate_fetch_request(
    host: _OpenAlexFilterFetchHost,
    request: _FetchRequest,
) -> AsyncIterator[BronzeRecord]:
    """Dispatch one normalized public fetch request."""
    if request.filter_ids:
        async for work in host.fetch_filtered(
            request.entity_type,
            request.filter_ids,
            request.filter_field or "doi",
            request.limit,
        ):
            yield work
        return

    host._validate_entity_type(request.entity_type)
    if not request.query:
        raise ValueError(
            "OpenAlex requires either filter_ids (DOIs) or query parameter"
        )

    async for work in host._fetch_by_query(
        query=request.query,
        limit=request.limit,
    ):
        yield work
