"""Batch processing utilities for CrossRef DOI resolution.

Provides batch DOI resolution and pagination support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.domain.normalization import normalize_doi
from bioetl.infrastructure.adapters.crossref.exceptions import CrossRefApiError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort

# Type aliases for helper class parameters
HttpTransport = Any
BaseMetrics = Any


class DoiBatchProcessor:
    """Handles batch DOI resolution for CrossRef API.

    Extracts batch processing logic to reduce main class size.
    """

    def __init__(
        self,
        http: HttpTransport,
        logger: LoggerPort,
        metrics: BaseMetrics,
        mailto: str,
        api_base: str,
        headers_fn: Any,  # Callable returning dict[str, str]
    ) -> None:
        """Initialize batch processor.

        Args:
            http: HTTP transport for making requests.
            logger: Logger port for structured logging.
            metrics: Metrics for request timing.
            mailto: Email for polite pool access.
            api_base: CrossRef API base URL.
            headers_fn: Function to build request headers.
        """
        self._http = http
        self._logger = logger
        self._metrics = metrics
        self._mailto = mailto
        self._api_base = api_base
        self._headers_fn = headers_fn

    async def fetch_single(self, doi: str) -> dict[str, Any] | None:
        """Fetch a single publication by DOI.

        Args:
            doi: The DOI to fetch (will be normalized).

        Returns:
            Publication record or None if not found.

        Raises:
            CrossRefApiError: On API errors (non-404).
        """
        normalized_doi = normalize_doi(doi) or ""
        url = f"{self._api_base}/works/{normalized_doi}"

        try:
            with self._metrics.measure_request("/works/{doi}"):
                response = await self._http.get(url, headers=self._headers_fn())

            if response.status_code == 404:
                self._logger.debug("crossref_doi_not_found", doi=normalized_doi)
                return None

            if response.status_code != 200:
                raise CrossRefApiError(
                    f"CrossRef API error for DOI {normalized_doi}",
                    status_code=response.status_code,
                )

            data = response.json()
            publication: dict[str, Any] = data.get("message", {})
            return publication

        except CrossRefApiError:
            raise
        except Exception as e:
            self._logger.error(
                "crossref_fetch_failed", doi=normalized_doi, error=str(e)
            )
            raise CrossRefApiError(f"Failed to fetch DOI {normalized_doi}: {e}") from e

    async def _fallback_individual_fetch(
        self, dois: list[str]
    ) -> AsyncIterator[dict[str, Any]]:
        """Fall back to individual DOI fetches."""
        for doi in dois:
            try:
                publication = await self.fetch_single(doi)
                if publication:
                    yield publication
            except Exception as e:
                self._logger.debug(
                    "crossref_individual_fetch_failed", doi=doi, error=str(e)
                )

    async def fetch_batch(self, dois: list[str]) -> AsyncIterator[dict[str, Any]]:
        """Fetch multiple publications by DOI batch.

        Uses CrossRef filter endpoint for batch resolution.

        Args:
            dois: List of DOIs to fetch (max 100).

        Yields:
            Publication records for found DOIs.
        """
        if not dois:
            return

        normalized_dois = [normalize_doi(d) or "" for d in dois]
        filter_value = ",".join(normalized_dois)
        url = f"{self._api_base}/works"
        params = {
            "filter": f"doi:{filter_value}",
            "rows": str(len(normalized_dois)),
            "mailto": self._mailto,
        }

        try:
            with self._metrics.measure_request("/works?filter=doi"):
                response = await self._http.get(
                    url, params=params, headers=self._headers_fn()
                )

            if response.status_code != 200:
                self._logger.warning(
                    "crossref_batch_fetch_failed",
                    status_code=response.status_code,
                    doi_count=len(dois),
                )
                async for publication in self._fallback_individual_fetch(dois):
                    yield publication
                return

            data = response.json()
            items = data.get("message", {}).get("items", [])
            for item in items:
                yield item

        except Exception as e:
            self._logger.warning(
                "crossref_batch_fetch_error", error=str(e), doi_count=len(dois)
            )
            async for publication in self._fallback_individual_fetch(dois):
                yield publication


class SearchPaginator:
    """Handles cursor-based pagination for CrossRef search.

    Extracts pagination logic to reduce main class size.
    """

    def __init__(
        self,
        http: HttpTransport,
        logger: LoggerPort,
        metrics: BaseMetrics,
        mailto: str,
        api_base: str,
        headers_fn: Any,  # Callable returning dict[str, str]
    ) -> None:
        """Initialize search paginator."""
        self._http = http
        self._logger = logger
        self._metrics = metrics
        self._mailto = mailto
        self._api_base = api_base
        self._headers_fn = headers_fn

    async def _fetch_page(
        self, query: str, rows: int, cursor: str
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Fetch a single page of search results."""
        url = f"{self._api_base}/works"
        params = {
            "query": query,
            "rows": str(rows),
            "cursor": cursor,
            "mailto": self._mailto,
        }

        with self._metrics.measure_request("/works?query"):
            response = await self._http.get(
                url, params=params, headers=self._headers_fn()
            )

        if response.status_code != 200:
            raise CrossRefApiError(
                f"CrossRef search failed: {response.status_code}",
                status_code=response.status_code,
            )

        data = response.json()
        message = data.get("message", {})
        items = message.get("items", [])
        next_cursor = message.get("next-cursor")

        return items, next_cursor

    async def search(
        self, query: str, limit: int | None = None, cursor: str = "*"
    ) -> AsyncIterator[dict[str, Any]]:
        """Search for publications using cursor-based pagination.

        Args:
            query: Search query string.
            limit: Maximum number of results.
            cursor: Pagination cursor (* for first page).

        Yields:
            Publication records matching the query.
        """
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

                # Check if pagination should continue
                if not items or not next_cursor or next_cursor == cursor:
                    break
                cursor = next_cursor

        except CrossRefApiError:
            raise
        except Exception as e:
            self._logger.error("crossref_search_failed", query=query, error=str(e))
            raise CrossRefApiError(f"CrossRef search failed: {e}") from e
