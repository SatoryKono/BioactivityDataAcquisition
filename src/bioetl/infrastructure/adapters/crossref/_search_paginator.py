"""Internal cursor-search workflow for the CrossRef adapter."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, cast

from httpx import Response

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.crossref._batch_support import (
    CROSSREF_RUNTIME_ERRORS,
    BaseMetrics,
    HeadersProvider,
    HttpTransport,
    record_response_timing,
)
from bioetl.infrastructure.adapters.crossref.exceptions import CrossRefApiError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )


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
        response: Response | None = None

        start_time = time.perf_counter()
        with self._metrics.measure_request("/works?query"):
            response = await self._http.get(
                url,
                params=params,
                headers=self._headers_fn(),
            )
        duration_ms = (time.perf_counter() - start_time) * 1000
        record_response_timing(
            self._request_collector,
            response,
            duration_ms,
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

        try:
            while True:
                items, next_cursor = await self._fetch_page(query, rows, cursor)

                for item in items:
                    yield item
                    fetched += 1
                    if limit and fetched >= limit:
                        return

                if not self._should_continue_pagination(items, next_cursor, cursor):
                    break
                assert next_cursor is not None
                cursor = next_cursor

        except CrossRefApiError:
            raise
        except CROSSREF_RUNTIME_ERRORS as error:
            self._logger.error("crossref_search_failed", query=query, error=str(error))
            raise CrossRefApiError(f"CrossRef search failed: {error}") from error
