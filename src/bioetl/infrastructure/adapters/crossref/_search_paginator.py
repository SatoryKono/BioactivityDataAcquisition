"""Internal cursor-search workflow for the CrossRef adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.crossref._batch_support import (
    CROSSREF_RUNTIME_ERRORS,
    BaseMetrics,
    HeadersProvider,
    HttpTransport,
    perform_timed_crossref_get,
)
from bioetl.infrastructure.adapters.crossref.exceptions import CrossRefApiError
from bioetl.infrastructure.adapters.http.pagination import (
    PaginationTruncatedError,
    raise_pagination_truncated,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )


# Hard ceiling against runaway cursor loops from misbehaving providers (CF-034).
_DEFAULT_MAX_PAGES: int = 10_000


class SearchPaginator:
    """Handles cursor-based pagination for CrossRef search."""

    def __init__(
        self,
        http: HttpTransport,
        logger: LoggerPort,
        metrics: BaseMetrics,
        mailto: str,
        api_base: str,
        headers_fn: HeadersProvider,
        request_collector: APIRequestCollector | None = None,
    ) -> None:
        self._http = http
        self._logger = logger
        self._metrics = metrics
        self._mailto = mailto
        self._api_base = api_base
        self._headers_fn = headers_fn
        self._request_collector = request_collector

    async def _fetch_page(
        self, query: str, rows: int, cursor: str
    ) -> tuple[list[BronzeRecord], str | None]:
        """Fetch a single page of search results."""
        url = f"{self._api_base}/works"
        params = {
            "query": query,
            "rows": str(rows),
            "cursor": cursor,
            "mailto": self._mailto,
        }
        response = await perform_timed_crossref_get(
            http=self._http,
            metrics=self._metrics,
            route="/works?query",
            url=url,
            params=params,
            headers=self._headers_fn(),
            request_collector=self._request_collector,
        )

        if response is None:
            self._logger.error(
                "crossref_search_failed",
                query=query,
                error="no_response",
            )
            raise CrossRefApiError("CrossRef search failed: no response")

        if response.status_code != 200:
            raise CrossRefApiError(
                f"CrossRef search failed: {response.status_code}",
                status_code=response.status_code,
            )

        data = response.json()
        message = data.get("message", {})
        if not isinstance(message, dict):
            raise CrossRefApiError("CrossRef search failed: invalid response body")

        items_raw = message.get("items", [])
        items = [
            cast(BronzeRecord, item) for item in items_raw if isinstance(item, dict)
        ]
        next_cursor_value = message.get("next-cursor")
        next_cursor = next_cursor_value if isinstance(next_cursor_value, str) else None
        return items, next_cursor

    def _should_continue_pagination(
        self, items: list[BronzeRecord], next_cursor: str | None, current_cursor: str
    ) -> bool:
        """Check if pagination should continue."""
        if not items:
            return False
        if not next_cursor:
            return False
        return next_cursor != current_cursor

    async def search(
        self, query: str, limit: int | None = None, cursor: str = "*"
    ) -> AsyncIterator[BronzeRecord]:
        """Search for publications using cursor-based pagination."""
        rows = min(limit, 100) if limit else 100
        fetched = 0
        page_count = 0
        seen_cursors: set[str] = {cursor}

        try:
            while True:
                if page_count >= _DEFAULT_MAX_PAGES:
                    raise_pagination_truncated(
                        self._logger,
                        event="crossref_search_truncated",
                        reason="max_pages",
                        page_count=page_count,
                        page_limit=_DEFAULT_MAX_PAGES,
                        cursor_field="next_cursor",
                        cursor_value=cursor[:100],
                        log_context={"query": query[:100]},
                    )
                page_count += 1
                items, next_cursor = await self._fetch_page(query, rows, cursor)

                for item in items:
                    yield item
                    fetched += 1
                    if limit and fetched >= limit:
                        return

                advanced = self._advance_search_cursor(
                    items=items,
                    next_cursor=next_cursor,
                    current_cursor=cursor,
                    seen_cursors=seen_cursors,
                    query=query,
                    page_count=page_count,
                )
                if advanced is None:
                    break
                cursor = advanced

        except (CrossRefApiError, PaginationTruncatedError):
            raise
        except CROSSREF_RUNTIME_ERRORS as error:
            self._logger.error("crossref_search_failed", query=query, error=str(error))
            raise CrossRefApiError(f"CrossRef search failed: {error}") from error

    def _advance_search_cursor(
        self,
        *,
        items: list[BronzeRecord],
        next_cursor: str | None,
        current_cursor: str,
        seen_cursors: set[str],
        query: str,
        page_count: int,
    ) -> str | None:
        """Stop on exhaustion or a cursor cycle before refetching a page."""
        if not items or not next_cursor:
            return None
        if next_cursor == current_cursor or next_cursor in seen_cursors:
            raise_pagination_truncated(
                self._logger,
                event="crossref_search_truncated",
                reason="repeated_cursor",
                page_count=page_count,
                page_limit=_DEFAULT_MAX_PAGES,
                cursor_field="next_cursor",
                cursor_value=next_cursor[:100],
                log_context={"query": query[:100]},
            )
        seen_cursors.add(next_cursor)
        return next_cursor
