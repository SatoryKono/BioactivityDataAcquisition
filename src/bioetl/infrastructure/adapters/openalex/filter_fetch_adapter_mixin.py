"""Fetch/filter orchestration mixin for OpenAlexAdapter."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord, JsonDict

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.openalex.cursor_flow import (
        OpenAlexCursorFlowService,
    )
    from bioetl.infrastructure.adapters.openalex.fallback_orchestrator import (
        OpenAlexFallbackOrchestrator,
    )
    from bioetl.infrastructure.adapters.openalex.query_execution import (
        OpenAlexQueryExecutor,
    )

_FilteredRecordFetcher = Callable[[list[str], int | None], AsyncIterator[BronzeRecord]]


@dataclass(frozen=True, slots=True)
class _FilteredFetchRequest:
    """Normalized request for one filtered OpenAlex fetch path."""

    entity_type: str
    filter_ids: list[str]
    filter_field: str
    limit: int | None = None


@dataclass(frozen=True, slots=True)
class _FallbackFetchRequest:
    """Normalized request for DOI-first fetch with title fallback."""

    entity_type: str
    filter_ids: list[str]
    filter_field: str
    fallback_mapping: dict[str, str]
    limit: int | None = None


@dataclass(frozen=True, slots=True)
class _FetchRequest:
    """Normalized request for the public OpenAlex fetch entrypoint."""

    entity_type: str
    limit: int | None = None
    query: str | None = None
    filter_ids: list[str] | None = None
    filter_field: str | None = None


def _create_filtered_fetch_request(
    host: OpenAlexAdapterFilterFetchMixin,
    *,
    entity_type: str,
    filter_ids: list[str],
    filter_field: str,
    limit: int | None,
) -> _FilteredFetchRequest:
    """Normalize and validate filtered fetch inputs."""
    host._validate_entity_type(entity_type)
    return _FilteredFetchRequest(
        entity_type=entity_type,
        filter_ids=filter_ids,
        filter_field=filter_field,
        limit=limit,
    )


def _create_fallback_fetch_request(
    host: OpenAlexAdapterFilterFetchMixin,
    *,
    entity_type: str,
    filter_ids: list[str],
    filter_field: str,
    fallback_mapping: dict[str, str],
    limit: int | None,
) -> _FallbackFetchRequest:
    """Normalize and validate fallback fetch inputs."""
    if not host._is_supported_entity_type(entity_type):
        raise ValueError(
            f"OpenAlexAdapter supports 'work'/'publication', got: {entity_type}"
        )
    return _FallbackFetchRequest(
        entity_type=entity_type,
        filter_ids=filter_ids,
        filter_field=filter_field,
        fallback_mapping=fallback_mapping,
        limit=limit,
    )


def _create_fetch_request(
    *,
    entity_type: str,
    limit: int | None,
    query: str | None,
    filter_ids: list[str] | None,
    filter_field: str | None,
) -> _FetchRequest:
    """Normalize public fetch inputs before dispatch."""
    return _FetchRequest(
        entity_type=entity_type,
        limit=limit,
        query=query,
        filter_ids=filter_ids,
        filter_field=filter_field,
    )


def _resolve_filtered_record_fetcher(
    host: OpenAlexAdapterFilterFetchMixin,
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


def _build_primary_record_fetcher(
    host: OpenAlexAdapterFilterFetchMixin,
) -> _FilteredRecordFetcher:
    """Build the DOI-first primary fetcher for fallback orchestration."""

    def _primary_records(
        primary_ids: list[str],
        request_limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        return host._batch_doi_lookup(primary_ids, request_limit)

    return _primary_records


async def _iterate_filtered_request(
    host: OpenAlexAdapterFilterFetchMixin,
    request: _FilteredFetchRequest,
) -> AsyncIterator[BronzeRecord]:
    """Execute one normalized filtered request."""
    fetcher = _resolve_filtered_record_fetcher(host, request.filter_field)
    if fetcher is None:
        return
    async for work in fetcher(request.filter_ids, request.limit):
        yield work


async def _iterate_fallback_request(
    host: OpenAlexAdapterFilterFetchMixin,
    request: _FallbackFetchRequest,
) -> AsyncIterator[BronzeRecord]:
    """Execute one normalized fallback request."""
    async for work in host._fallback_orchestrator.execute(
        filter_ids=request.filter_ids,
        fallback_mapping=request.fallback_mapping,
        primary_record_fetcher=_build_primary_record_fetcher(host),
        limit=request.limit,
        filter_field=request.filter_field,
    ):
        yield work


async def _iterate_fetch_request(
    host: OpenAlexAdapterFilterFetchMixin,
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


class OpenAlexAdapterFilterFetchMixin:
    """OpenAlex fetch/filter orchestration for FilterableDataSourcePort behavior."""

    logger: LoggerPort
    _logger: LoggerPort
    _query_executor: OpenAlexQueryExecutor
    _cursor_flow: OpenAlexCursorFlowService
    _fallback_orchestrator: OpenAlexFallbackOrchestrator

    @staticmethod
    def _is_supported_entity_type(entity_type: str) -> bool:
        return entity_type in ("work", "publication")

    def _validate_entity_type(self, entity_type: str) -> None:
        if self._is_supported_entity_type(entity_type):
            return
        raise ValueError(
            f"OpenAlexAdapter supports 'work' or 'publication', got: {entity_type}"
        )

    async def _request_works_payload(
        self,
        params: dict[str, str],
    ) -> JsonDict:  # Any: untyped OpenAlex API payload
        """Backward-compatible wrapper around query-execution component."""
        return await self._query_executor.request_works_payload(params)

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch OpenAlex records by DOI/title."""
        request = _create_filtered_fetch_request(
            self,
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=limit,
        )
        async for work in _iterate_filtered_request(self, request):
            yield work

    async def _fetch_filtered_by_doi(
        self,
        filter_ids: list[str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch OpenAlex works by DOI list."""
        async for work in self._cursor_flow.iter_filtered_by_doi(filter_ids, limit):
            yield work

    async def _fetch_filtered_by_title(
        self,
        titles: list[str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch works by title."""
        async for work in self._cursor_flow.iter_filtered_by_title(titles, limit):
            yield work

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Multi-field filtering is not supported by OpenAlex."""
        raise NotImplementedError(
            "OpenAlex adapter does not support multi-field filtering. "
            "Use fetch_filtered() with filter_field='doi' instead."
        )
        yield {}  # pragma: no cover - keeps AsyncIterator contract

    async def _batch_doi_lookup(
        self,
        valid_dois: list[str],
        limit: int | None,
        start_count: int = 0,
    ) -> AsyncIterator[BronzeRecord]:
        """Phase-1 DOI lookup via cursor-flow."""
        async for work in self._cursor_flow.iter_doi_batches_for_fallback(
            primary_ids=valid_dois,
            limit=limit,
            start_count=start_count,
        ):
            yield work

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch DOI-first records with title fallback resolution."""
        request = _create_fallback_fetch_request(
            self,
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            fallback_mapping=fallback_mapping,
            limit=limit,
        )
        async for work in _iterate_fallback_request(self, request):
            yield work

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch OpenAlex works by filters or free-text query."""
        request = _create_fetch_request(
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        )
        async for work in _iterate_fetch_request(self, request):
            yield work

    async def _fetch_by_query(
        self,
        *,
        query: str,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch works with cursor pagination."""
        async for work in self._cursor_flow.iter_query_results(
            query=query,
            limit=limit,
        ):
            yield work

    async def _fetch_by_dois(self, dois: list[str]) -> AsyncIterator[BronzeRecord]:
        """Fetch works by DOI in a single batch."""
        async for work in self._cursor_flow.iter_by_dois(dois):
            yield work

    async def _search_by_title(
        self,
        title: str,
        limit: int = 3,
    ) -> list[BronzeRecord]:
        """Search works by title."""
        return await self._cursor_flow.search_by_title(title, limit)


__all__ = ["OpenAlexAdapterFilterFetchMixin"]
