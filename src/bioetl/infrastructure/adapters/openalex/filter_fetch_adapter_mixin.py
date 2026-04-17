"""Fetch/filter orchestration mixin for OpenAlexAdapter."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord, JsonDict
from bioetl.infrastructure.adapters.filterable_mixin import raising_async_iterator
from bioetl.infrastructure.adapters.openalex._filter_fetch_flow import (
    iterate_fallback_request,
    iterate_fetch_request,
    iterate_filtered_request,
)
from bioetl.infrastructure.adapters.openalex._filter_fetch_requests import (
    create_fallback_fetch_request,
    create_fetch_request,
    create_filtered_fetch_request,
)

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
        request = create_filtered_fetch_request(
            self,
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=limit,
        )
        async for work in iterate_filtered_request(self, request):
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

    def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Multi-field filtering is not supported by OpenAlex."""
        del entity_type, filters, limit
        return raising_async_iterator(
            NotImplementedError(
                "OpenAlex adapter does not support multi-field filtering. "
                "Use fetch_filtered() with filter_field='doi' instead."
            )
        )

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
        request = create_fallback_fetch_request(
            self,
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            fallback_mapping=fallback_mapping,
            limit=limit,
        )
        async for work in iterate_fallback_request(self, request):
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
        del offset
        request = create_fetch_request(
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        )
        async for work in iterate_fetch_request(self, request):
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
