"""Bounded free-text query pagination for OpenAlex."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.http.pagination import raise_pagination_truncated
from bioetl.infrastructure.adapters.openalex.query_builder import (
    build_openalex_search_params,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.openalex.query_execution import (
        OpenAlexQueryExecutor,
    )
    from bioetl.infrastructure.adapters.openalex.response_mapping import (
        OpenAlexResponseMapper,
    )


async def iter_query_results(
    *,
    query: str,
    limit: int | None,
    max_pages: int,
    batch_size: int,
    mailto: str | None,
    api_key: str | None,
    query_executor: OpenAlexQueryExecutor,
    response_mapper: OpenAlexResponseMapper,
    logger: LoggerPort,
) -> AsyncIterator[BronzeRecord]:
    """Yield query results, stopping at limits or before revisiting any cursor."""
    if limit is not None and limit <= 0:
        return
    fetched = 0
    cursor: str = "*"
    per_page = min(batch_size, 200)
    page_count = 0
    seen_cursors: set[str] = {cursor}

    while cursor:
        if page_count >= max_pages:
            raise_pagination_truncated(
                logger,
                event="openalex_query_results_truncated",
                reason="max_pages",
                page_count=page_count,
                page_limit=max_pages,
                cursor_field="next_cursor",
                cursor_value=cursor[:100],
                log_context={"query": query[:100]},
            )
        page_count += 1
        params = build_openalex_search_params(
            mailto=mailto,
            api_key=api_key,
            query=query,
            cursor=cursor,
            per_page=per_page,
        )
        payload = await query_executor.request_works_payload(params)
        for work in response_mapper.extract_results(payload):
            yield work
            fetched += 1
            if limit is not None and fetched >= limit:
                return
        next_cursor = response_mapper.extract_next_cursor(payload)
        if next_cursor is None:
            break
        if next_cursor in seen_cursors:
            raise_pagination_truncated(
                logger,
                event="openalex_query_results_truncated",
                reason="repeated_cursor",
                page_count=page_count,
                page_limit=max_pages,
                cursor_field="next_cursor",
                cursor_value=next_cursor[:100],
                log_context={"query": query[:100]},
            )
        seen_cursors.add(next_cursor)
        cursor = next_cursor
