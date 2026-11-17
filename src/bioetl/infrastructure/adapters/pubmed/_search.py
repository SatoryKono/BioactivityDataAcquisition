"""Search functionality for PubMed adapter.

Part of PubMedAdapter split to comply with LOC limits.
"""

from __future__ import annotations

import contextlib
import time
from typing import TYPE_CHECKING

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.http.pagination import PaginationTruncatedError
from bioetl.infrastructure.adapters.pubmed._errors import (
    PUBMED_RECORD_ERRORS as PUBMED_SEARCH_ERRORS,
)
from bioetl.infrastructure.adapters.pubmed._errors import (
    PubMedSearchPayloadError,
    parse_esearch_payload,
)
from bioetl.infrastructure.adapters.pubmed._search_models import (
    MAX_ESEARCH_PAGES,
    append_completed_page,
    esearch_page_completes,
    esearch_params,
    esearch_result_still_short,
    raise_pubmed_search_truncated,
    reject_esearch_page_cap,
    reject_short_esearch_result,
    reject_stalled_esearch_page,
)
from bioetl.infrastructure.adapters.pubmed._state import PubMedAdapterStateMixin

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from .constants import ENTREZ_API_BASE

__all__ = ["PUBMED_SEARCH_ERRORS", "PubMedSearchMixin"]

_ESEARCH_URL = f"{ENTREZ_API_BASE}esearch.fcgi"


class PubMedSearchMixin(PubMedAdapterStateMixin):
    """Mixin providing search capabilities for PubMed."""

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
            PMID strings up to ``max_count``. A filled ``max_count`` stays a ceiling
            when ESearch ``count`` is larger. A shorter page is followed with
            ``retstart`` or rejected as truncation.

        Raises:
            PaginationTruncatedError: ``count`` exceeds the collected ids, a
                later page does not advance, or the ESearch payload is not a
                result object.
        """
        try:
            return await PubMedSearchMixin._collect_pmids(self, search_term, max_count)
        except PaginationTruncatedError:
            raise
        except PUBMED_SEARCH_ERRORS as error:
            wrapped = self._error_handler.handle_error(
                error=error,
                provider=self.provider_name,
                operation="search",
                context={"search_term": search_term, "max_count": max_count},
            )
            raise wrapped from error

    async def _collect_pmids(self, search_term: str, max_count: int) -> list[str]:
        """Page ESearch until ``max_count`` or the reported ``count`` is covered."""
        collected: list[str] = []
        retstart = 0
        reported_count: int | None = None
        seen_pages: set[tuple[str, ...]] = set()
        page_count = 0
        for page_count in range(1, MAX_ESEARCH_PAGES + 1):
            if len(collected) >= max_count:
                break
            try:
                (
                    page_ids,
                    page_count_value,
                ) = await PubMedSearchMixin._fetch_esearch_page(
                    self,
                    search_term,
                    retstart=retstart,
                    retmax=max_count - len(collected),
                )
            except PubMedSearchPayloadError:
                raise_pubmed_search_truncated(
                    self._logger,
                    reason="malformed_payload",
                    page_count=page_count,
                    retstart=retstart,
                    reported_count=reported_count,
                    collected_count=len(collected),
                    max_count=max_count,
                )
            if page_count_value is not None:
                reported_count = page_count_value
            if esearch_result_still_short(len(collected), max_count, reported_count):
                reject_stalled_esearch_page(
                    self,
                    page_ids,
                    seen_pages,
                    page_count=page_count,
                    retstart=retstart,
                    reported_count=reported_count,
                    collected_count=len(collected),
                    max_count=max_count,
                )
            if esearch_page_completes(collected, page_ids, max_count, reported_count):
                append_completed_page(collected, page_ids, max_count, reported_count)
                break
            seen_pages.add(tuple(page_ids))
            collected.extend(page_ids)
            retstart += len(page_ids)
        else:
            reject_esearch_page_cap(
                self,
                page_count=page_count,
                retstart=retstart,
                reported_count=reported_count,
                collected_count=len(collected),
                max_count=max_count,
            )
        reject_short_esearch_result(
            self,
            collected,
            max_count=max_count,
            reported_count=reported_count,
            page_count=page_count,
            retstart=retstart,
        )
        return collected[:max_count]

    async def _fetch_esearch_page(
        self,
        search_term: str,
        *,
        retstart: int,
        retmax: int,
    ) -> tuple[list[str], int | None]:
        """Request one ESearch page and return its ids plus parsed ``count``."""
        params = esearch_params(
            self.email,
            self.api_key,
            search_term,
            retstart=retstart,
            retmax=retmax,
        )
        start_time = time.perf_counter()
        with self._adapter_metrics.measure_request("/esearch"):
            response = await self.http_client.get(_ESEARCH_URL, params=params)
        duration_ms = (time.perf_counter() - start_time) * 1000
        with contextlib.suppress(Exception):
            self._request_collector.record_from_response(response, duration_ms)
        return parse_esearch_payload(response.json())

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
        except PaginationTruncatedError:
            raise
        except PUBMED_SEARCH_ERRORS as error:
            self._logger.debug(
                "pubmed_title_search_failed",
                title=clean_title[:50],
                error=str(error),
            )
            return []
