"""Search functionality for PubMed adapter.

Part of PubMedAdapter split to comply with LOC limits.
"""

from __future__ import annotations

from bioetl.domain.types import JsonDict

__all__ = ["PUBMED_SEARCH_ERRORS", "PubMedSearchMixin"]

import contextlib
import time
from typing import TYPE_CHECKING

from bioetl.infrastructure.adapters.pubmed._errors import (
    PUBMED_RECORD_ERRORS as PUBMED_SEARCH_ERRORS,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

from .constants import ENTREZ_API_BASE


class PubMedSearchMixin:
    """Mixin providing search capabilities for PubMed."""

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    email: str
    api_key: str | None
    _http_client: UnifiedHTTPClient
    _logger: LoggerPort
    _adapter_metrics: AdapterMetricsRecorder
    _request_collector: APIRequestCollector
    _error_handler: ErrorHandlerPort
    provider_name: str
    batch_size: int
    metrics: MetricsPort | None

    # Provided by PubMedFetchMixin in the concrete class
    def _yield_articles_from_pmids(
        self, pmids: list[str], limit: int | None
    ) -> AsyncIterator[JsonDict]:  # Any: untyped API JSON record
        raise NotImplementedError  # mixin stub; overridden by PubMedFetchMixin

    async def _get_pmids(self, search_term: str, max_count: int) -> list[str]:
        """Get PMIDs for a search term.

        Args:
            search_term: Entrez search query string (e.g., ``"cancer AND 2023[dp]"``).
            max_count: Maximum number of PMIDs to retrieve from the esearch endpoint.

        Returns:
            List of PMID strings matching the search term, up to max_count results.
        """
        search_url = f"{ENTREZ_API_BASE}esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": search_term,
            "retmax": str(max_count),
            "usehistory": "y",
            "retmode": "json",
            "email": self.email,
        }
        if self.api_key and "your_" not in self.api_key:
            params["api_key"] = self.api_key

        try:
            start_time = time.perf_counter()
            with self._adapter_metrics.measure_request("/esearch"):
                response = await self._http_client.get(search_url, params=params)
            duration_ms = (time.perf_counter() - start_time) * 1000

            with contextlib.suppress(Exception):
                self._request_collector.record_from_response(response, duration_ms)

            data = response.json()
            idlist: list[str] = data.get("esearchresult", {}).get("idlist", [])
            return idlist
        except PUBMED_SEARCH_ERRORS as e:
            wrapped = self._error_handler.handle_error(
                error=e,
                provider=self.provider_name,
                operation="search",
                context={"search_term": search_term, "max_count": max_count},
            )
            raise wrapped from e

    async def _search_by_title(
        self, title: str, limit: int = 3
    ) -> list[JsonDict]:  # Any: untyped API JSON record
        """Search PubMed by title using esearch + efetch.

        Returns:
            List of article record dictionaries matching the title search, up to limit results.
        """
        clean_title = title.replace('"', "'").strip()[:200]
        search_term = f'"{clean_title}"[Title]'

        self._logger.debug(
            "pubmed_title_search",
            title=clean_title[:50],
        )

        try:
            pmids = await self._get_pmids(search_term, limit)
            if not pmids:
                return []

            results: list[JsonDict] = []  # Any: untyped API JSON record
            async for record in self._yield_articles_from_pmids(pmids, limit):
                results.append(record)

            return results
        except PUBMED_SEARCH_ERRORS as e:
            self._logger.debug(
                "pubmed_title_search_failed",
                title=clean_title[:50],
                error=str(e),
            )
            return []
