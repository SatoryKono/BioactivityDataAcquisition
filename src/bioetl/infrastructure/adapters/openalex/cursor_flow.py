"""Cursor-flow and filtered-fetch component for OpenAlex adapter."""

from __future__ import annotations

__all__ = ["OpenAlexCursorFlowService"]

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.openalex.query_builder import (
    build_openalex_doi_filter_params,
    build_openalex_search_params,
    build_openalex_title_search_params,
)
from bioetl.infrastructure.adapters.openalex.query_execution import (
    OpenAlexQueryExecutor,
)
from bioetl.infrastructure.adapters.openalex.response_mapping import (
    OpenAlexResponseMapper,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@dataclass(slots=True)
class OpenAlexCursorFlowService:
    """Encapsulates OpenAlex pagination/query/filter/title-search flows."""

    mailto: str | None
    batch_size: int
    title_search_cache_size: int
    normalize_doi: Callable[[str], str | None]
    escape_title_for_search: Callable[[str], str]
    query_executor: OpenAlexQueryExecutor
    response_mapper: OpenAlexResponseMapper
    logger: LoggerPort
    runtime_errors: tuple[type[Exception], ...]
    api_key: str | None = None
    _title_search_cache: dict[tuple[str, int], list[BronzeRecord]] = field(
        init=False,
        default_factory=dict,
    )

    async def iter_query_results(
        self,
        *,
        query: str,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Yield free-text query results using OpenAlex cursor pagination.

        Args:
            query: Free-text search query string for the OpenAlex works endpoint.
            limit: Optional maximum number of records to yield.

        Yields:
            BronzeRecord works from the OpenAlex search results.
        """
        fetched = 0
        cursor: str | None = "*"
        per_page = min(self.batch_size, 200)

        while cursor:
            params = build_openalex_search_params(
                mailto=self.mailto,
                api_key=self.api_key,
                query=query,
                cursor=cursor,
                per_page=per_page,
            )
            payload = await self.query_executor.request_works_payload(params)
            for work in self.response_mapper.extract_results(payload):
                if limit is not None and fetched >= limit:
                    return
                yield work
                fetched += 1
            cursor = self.response_mapper.extract_next_cursor(payload)

    async def iter_filtered_by_doi(
        self,
        filter_ids: list[str],
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Yield DOI-filtered works with `_lookup_method='doi'` metadata.

        Args:
            filter_ids: List of DOI strings to resolve via batch filter.
            limit: Optional maximum number of records to yield.

        Yields:
            BronzeRecord works with _lookup_method set to "doi".
        """
        dois = filter_ids[:limit] if limit is not None else filter_ids
        fetched = 0
        for batch_start in range(0, len(dois), self.batch_size):
            batch = dois[batch_start : batch_start + self.batch_size]
            async for work in self.iter_by_dois(batch):
                if limit is not None and fetched >= limit:
                    return
                yield self.response_mapper.mark_lookup(work, lookup_method="doi")
                fetched += 1

    async def iter_filtered_by_title(
        self,
        titles: list[str],
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Yield title-filtered works with lookup metadata and summary logging.

        Args:
            titles: List of publication title strings to search for.
            limit: Optional maximum number of records to yield.

        Yields:
            BronzeRecord works with _lookup_method set to "title".
        """
        self.logger.info(
            "openalex_title_search_start",
            total_titles=len(titles),
            limit=limit,
        )
        fetched = 0
        found = 0
        effective_titles = titles[:limit] if limit is not None else titles
        for title in effective_titles:
            if limit is not None and fetched >= limit:
                break
            if not title or not title.strip():
                continue
            results = await self.search_by_title(title, limit=1)
            if not results:
                continue
            yield self.response_mapper.mark_lookup(
                results[0],
                lookup_method="title",
                original_id=title,
                search_title=title,
            )
            found += 1
            fetched += 1
        self.logger.info(
            "openalex_title_lookup_summary",
            total_titles=len(effective_titles),
            found_by_title=found,
            hit_rate_pct=(
                round(found / len(effective_titles) * 100, 1)
                if effective_titles
                else 0.0
            ),
        )

    async def iter_doi_batches_for_fallback(
        self,
        primary_ids: list[str],
        limit: int | None,
        start_count: int = 0,
    ) -> AsyncIterator[BronzeRecord]:
        """Yield DOI-batch phase used by fallback orchestrator.

        Args:
            primary_ids: List of DOI strings for primary batch resolution.
            limit: Optional maximum total records to yield.
            start_count: Records already yielded before this phase, used to track against limit.

        Yields:
            BronzeRecord works with _lookup_method set to "doi".
        """
        count = start_count
        for batch_start in range(0, len(primary_ids), self.batch_size):
            if limit is not None and count >= limit:
                return
            batch = primary_ids[batch_start : batch_start + self.batch_size]
            async for work in self.iter_by_dois(batch):
                if limit is not None and count >= limit:
                    return
                yield self.response_mapper.mark_lookup(work, lookup_method="doi")
                count += 1

    async def iter_by_dois(self, dois: list[str]) -> AsyncIterator[BronzeRecord]:
        """Yield works resolved via batch DOI filter query.

        Args:
            dois: List of DOI strings to resolve in a single batch request.

        Yields:
            BronzeRecord works from the batch DOI filter response.
        """
        results = await self.fetch_by_dois(dois)
        for work in results:
            yield work

    async def fetch_by_dois(self, dois: list[str]) -> list[BronzeRecord]:
        """Resolve DOI batch and return records list.

        Args:
            dois: List of DOI strings to resolve via filter query.

        Returns:
            List of BronzeRecord dictionaries resolved from the DOI batch.
        """
        normalized = self._normalize_dois(dois)
        if not normalized:
            return []

        params = build_openalex_doi_filter_params(
            mailto=self.mailto,
            api_key=self.api_key,
            dois=normalized,
        )
        self.logger.debug("openalex_batch_doi_request", doi_count=len(normalized))
        payload = await self.query_executor.request_works_payload(params)
        results = self.response_mapper.extract_results(payload)
        if len(results) < len(normalized):
            self.logger.info(
                "openalex_batch_partial_results",
                requested=len(normalized),
                found=len(results),
                hit_rate=round(len(results) / len(normalized) * 100, 1),
            )
        return results

    async def search_by_title(self, title: str, limit: int = 3) -> list[BronzeRecord]:
        """Search by title with in-memory cache and graceful runtime fallback.

        Args:
            title: Publication title string to search for.
            limit: Maximum number of results to return per search.

        Returns:
            List of BronzeRecord dictionaries matching the title search, up to limit results.
        """
        normalized_title = title.strip()
        cache_key = (normalized_title.casefold(), limit)
        cached = self._title_search_cache.get(cache_key)
        if cached is not None:
            return [dict(item) for item in cached]

        params = build_openalex_title_search_params(
            mailto=self.mailto,
            api_key=self.api_key,
            escaped_title=self.escape_title_for_search(normalized_title[:200]),
            limit=limit,
        )
        self.logger.debug("openalex_title_search", title=title[:50])
        try:
            payload = await self.query_executor.request_works_payload(params)
            results = self.response_mapper.extract_results(payload)
        except self.runtime_errors as error:
            self.logger.debug(
                "openalex_title_search_failed",
                title=title[:50],
                error=str(error),
            )
            self._title_search_cache[cache_key] = []
            return []

        cached_results = [dict(item) for item in results]
        self._title_search_cache[cache_key] = cached_results
        if len(self._title_search_cache) > self.title_search_cache_size:
            oldest_key = next(iter(self._title_search_cache))
            del self._title_search_cache[oldest_key]
        return [dict(item) for item in cached_results]

    def _normalize_dois(self, dois: list[str]) -> list[str]:
        normalized_raw = [self.normalize_doi(item) for item in dois if item]
        return [doi for doi in normalized_raw if doi is not None]
