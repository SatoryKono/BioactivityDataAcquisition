"""Search functionality for PubMed adapter.

Part of PubMedAdapter split to comply with LOC limits.
"""

from __future__ import annotations

import contextlib
import time
from typing import TYPE_CHECKING, Any

from bioetl.infrastructure.adapters.pubmed.xml_processor import PubMedXmlProcessor

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
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
    _adapter_metrics: AdapterMetrics
    _request_collector: APIRequestCollector
    provider_name: str
    batch_size: int

    async def _get_pmids(self, search_term: str, max_count: int) -> list[str]:
        """Get PMIDs for a search term."""
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
                response = await self.http_client.get(search_url, params=params)
            duration_ms = (time.perf_counter() - start_time) * 1000

            with contextlib.suppress(Exception):
                self._request_collector.record_from_response(response, duration_ms)

            data = response.json()
            idlist: list[str] = data.get("esearchresult", {}).get("idlist", [])
            return idlist
        except Exception as e:
            from bioetl.infrastructure.adapters.error_handling import ErrorService

            error_handler = ErrorService(self.logger)
            wrapped = error_handler.handle_error(
                error=e,
                provider=self.provider_name,
                operation="search",
                context={"search_term": search_term, "max_count": max_count},
            )
            raise wrapped from e

    async def _search_by_title(
        self, title: str, limit: int = 3
    ) -> list[dict[str, Any]]:
        """Search PubMed by title using esearch + efetch."""
        clean_title = title.replace('"', "'").strip()[:200]
        search_term = f'"{clean_title}"[Title]'

        self.logger.debug(
            "pubmed_title_search",
            title=clean_title[:50],
        )

        try:
            pmids = await self._get_pmids(search_term, limit)
            if not pmids:
                return []

            results: list[dict[str, Any]] = []
            # Note: _yield_articles_from_pmids is expected to be in PubMedFetchMixin
            async for record in self._yield_articles_from_pmids(pmids, limit):  # type: ignore
                results.append(record)

            return results
        except Exception as e:
            self.logger.debug(
                "pubmed_title_search_failed",
                title=clean_title[:50],
                error=str(e),
            )
            return []
