"""Fetch/filter orchestration mixin for OpenAlexAdapter.

Implements FilterableDataSourcePort contract for filtered API access.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import BronzeRecord, JsonDict

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

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


class _OpenAlexFilterFetchHost(Protocol):
    """Structural host contract for OpenAlex fetch/filter mixin."""

    logger: LoggerPort
    _query_executor: OpenAlexQueryExecutor
    _cursor_flow: OpenAlexCursorFlowService
    _fallback_orchestrator: OpenAlexFallbackOrchestrator

    @staticmethod
    def _is_supported_entity_type(entity_type: str) -> bool:
        """Check supported OpenAlex entity types."""
        ...

    def _validate_entity_type(
        self,
        entity_type: str,
    ) -> None:
        """Validate OpenAlex entity type."""
        ...

    def _fetch_filtered_by_doi(
        self,
        filter_ids: list[str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch by DOI list."""
        ...

    def _fetch_filtered_by_title(
        self,
        titles: list[str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch by title list."""
        ...

    def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch filtered records."""
        ...

    def _batch_doi_lookup(
        self,
        valid_dois: list[str],
        limit: int | None,
        start_count: int = 0,
    ) -> AsyncIterator[BronzeRecord]:
        """Batch DOI lookup for fallback."""
        ...

    def _fetch_by_query(
        self,
        *,
        query: str,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch by query."""
        ...

    @staticmethod
    def _normalize_doi(doi: str) -> str | None:
        """Normalize DOI values."""
        ...

    @staticmethod
    def _extract_doi_from_record(record: BronzeRecord) -> str | None:
        """Extract DOI from OpenAlex record."""
        ...


class OpenAlexAdapterFilterFetchMixin:
    """OpenAlex fetch/filter orchestration for FilterableDataSourcePort behavior."""

    @staticmethod
    def _is_supported_entity_type(entity_type: str) -> bool:
        return entity_type in ("work", "publication")

    def _validate_entity_type(
        self: _OpenAlexFilterFetchHost,
        entity_type: str,
    ) -> None:
        if self._is_supported_entity_type(entity_type):
            return
        raise ValueError(
            f"OpenAlexAdapter supports 'work' or 'publication', got: {entity_type}"
        )

    async def _request_works_payload(
        self: _OpenAlexFilterFetchHost,
        params: dict[str, str],
    ) -> JsonDict:  # Any: untyped OpenAlex API payload
        """Backward-compatible wrapper around query-execution component.

        Returns:
            Dictionary containing the decoded JSON payload from the API response.
        """
        return await self._query_executor.request_works_payload(params)

    async def fetch_filtered(
        self: _OpenAlexFilterFetchHost,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch OpenAlex records by DOI/title via FilterableDataSourcePort contract."""
        self._validate_entity_type(entity_type)

        if filter_field == "doi":
            async for work in self._fetch_filtered_by_doi(filter_ids, limit):
                yield work
            return
        if filter_field == "title":
            async for work in self._fetch_filtered_by_title(filter_ids, limit):
                yield work
            return

        self.logger.warning(
            "unsupported_filter_field",
            field=filter_field,
            msg="OpenAlex only supports 'doi' or 'title' filtering, skipping",
        )

    async def _fetch_filtered_by_doi(
        self: _OpenAlexFilterFetchHost,
        filter_ids: list[str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch OpenAlex works by DOI list via cursor-flow component."""
        async for work in self._cursor_flow.iter_filtered_by_doi(filter_ids, limit):
            yield work

    async def _fetch_filtered_by_title(
        self: _OpenAlexFilterFetchHost,
        titles: list[str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch works by title via cursor-flow component."""
        async for work in self._cursor_flow.iter_filtered_by_title(titles, limit):
            yield work

    async def fetch_multi_filtered(
        self: _OpenAlexFilterFetchHost,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Multi-field filtering not supported by OpenAlex."""
        raise NotImplementedError(
            "OpenAlex adapter does not support multi-field filtering. "
            "Use fetch_filtered() with filter_field='doi' instead."
        )
        yield {}  # pragma: no cover - keeps AsyncIterator contract

    async def _batch_doi_lookup(
        self: _OpenAlexFilterFetchHost,
        valid_dois: list[str],
        limit: int | None,
        start_count: int = 0,
    ) -> AsyncIterator[BronzeRecord]:
        """Phase-1 DOI lookup via cursor-flow component."""
        async for work in self._cursor_flow.iter_doi_batches_for_fallback(
            primary_ids=valid_dois,
            limit=limit,
            start_count=start_count,
        ):
            yield work

    async def fetch_filtered_with_fallback(
        self: _OpenAlexFilterFetchHost,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch DOI-first records with title fallback resolution."""
        if not self._is_supported_entity_type(entity_type):
            raise ValueError(
                f"OpenAlexAdapter supports 'work'/'publication', got: {entity_type}"
            )

        def _primary_records(
            primary_ids: list[str], request_limit: int | None
        ) -> AsyncIterator[BronzeRecord]:
            return self._batch_doi_lookup(primary_ids, request_limit)

        async for work in self._fallback_orchestrator.execute(
            filter_ids=filter_ids,
            fallback_mapping=fallback_mapping,
            primary_record_fetcher=_primary_records,
            limit=limit,
            filter_field=filter_field,
        ):
            yield work

    async def fetch(
        self: _OpenAlexFilterFetchHost,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch OpenAlex works by filters or free-text query."""
        if filter_ids:
            effective_filter_field = filter_field or "doi"
            async for work in self.fetch_filtered(
                entity_type, filter_ids, effective_filter_field, limit
            ):
                yield work
            return

        self._validate_entity_type(entity_type)
        if not query:
            raise ValueError(
                "OpenAlex requires either filter_ids (DOIs) or query parameter"
            )

        async for work in self._fetch_by_query(query=query, limit=limit):
            yield work

    async def _fetch_by_query(
        self: _OpenAlexFilterFetchHost,
        *,
        query: str,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch works with cursor pagination via cursor-flow component."""
        async for work in self._cursor_flow.iter_query_results(
            query=query, limit=limit
        ):
            yield work

    async def _fetch_by_dois(
        self: _OpenAlexFilterFetchHost,
        dois: list[str],
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch works by DOI via cursor-flow component."""
        async for work in self._cursor_flow.iter_by_dois(dois):
            yield work

    async def _search_by_title(
        self: _OpenAlexFilterFetchHost,
        title: str,
        limit: int = 3,
    ) -> list[BronzeRecord]:
        """Search works by title via cursor-flow component.

        Returns:
            List of matching BronzeRecord dictionaries from the title search.
        """
        return await self._cursor_flow.search_by_title(title, limit)


__all__ = ["OpenAlexAdapterFilterFetchMixin"]
