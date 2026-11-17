"""Search functionality for PubMed adapter.

Part of PubMedAdapter split to comply with LOC limits.
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Mapping
from typing import TYPE_CHECKING

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.http.pagination import (
    PaginationTruncatedError,
    raise_pagination_truncated,
)
from bioetl.infrastructure.adapters.pubmed._errors import (
    PUBMED_RECORD_ERRORS as PUBMED_SEARCH_ERRORS,
)
from bioetl.infrastructure.adapters.pubmed._state import PubMedAdapterStateMixin

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from .constants import ENTREZ_API_BASE

__all__ = ["PUBMED_SEARCH_ERRORS", "PubMedSearchMixin"]

_ESEARCH_URL = f"{ENTREZ_API_BASE}esearch.fcgi"
_MAX_ESEARCH_PAGES = 10_000


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
            PaginationTruncatedError: ``count`` exceeds the collected ids and
                another ``retstart`` page does not advance the scan.
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
        for page_count in range(1, _MAX_ESEARCH_PAGES + 1):
            if len(collected) >= max_count:
                break
            page_ids, page_count_value = await PubMedSearchMixin._fetch_esearch_page(
                self,
                search_term,
                retstart=retstart,
                retmax=max_count - len(collected),
            )
            if page_count_value is not None:
                reported_count = page_count_value
            if _esearch_result_still_short(len(collected), max_count, reported_count):
                PubMedSearchMixin._reject_stalled_esearch_page(
                    self,
                    page_ids,
                    seen_pages,
                    page_count=page_count,
                    retstart=retstart,
                    reported_count=reported_count,
                    collected_count=len(collected),
                    max_count=max_count,
                )
            if _esearch_page_completes(collected, page_ids, max_count, reported_count):
                _append_completed_page(collected, page_ids, max_count, reported_count)
                break
            seen_pages.add(tuple(page_ids))
            collected.extend(page_ids)
            retstart += len(page_ids)
        else:
            PubMedSearchMixin._reject_esearch_page_cap(
                self,
                page_count=page_count,
                retstart=retstart,
                reported_count=reported_count,
                collected_count=len(collected),
                max_count=max_count,
            )
        PubMedSearchMixin._reject_short_esearch_result(
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
        params = _esearch_params(
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
        return _parse_esearch_payload(response.json())

    def _reject_stalled_esearch_page(
        self,
        page_ids: list[str],
        seen_pages: set[tuple[str, ...]],
        *,
        page_count: int,
        retstart: int,
        reported_count: int | None,
        collected_count: int,
        max_count: int,
    ) -> None:
        """Fail when the next page is empty or repeats a previous id list."""
        reason = _esearch_stall_reason(page_ids, seen_pages)
        if reason is None:
            return
        _raise_pubmed_search_truncated(
            self,
            reason=reason,
            page_count=page_count,
            retstart=retstart,
            reported_count=reported_count,
            collected_count=collected_count,
            max_count=max_count,
        )

    def _reject_esearch_page_cap(
        self,
        *,
        page_count: int,
        retstart: int,
        reported_count: int | None,
        collected_count: int,
        max_count: int,
    ) -> None:
        """Fail when paging hits the hard page ceiling before ``count``."""
        _raise_pubmed_search_truncated(
            self,
            reason="max_pages",
            page_count=page_count,
            retstart=retstart,
            reported_count=reported_count,
            collected_count=collected_count,
            max_count=max_count,
        )

    def _reject_short_esearch_result(
        self,
        collected: list[str],
        *,
        max_count: int,
        reported_count: int | None,
        page_count: int,
        retstart: int,
    ) -> None:
        """Fail when the collected ids are still shorter than ``count``."""
        target = _esearch_target(max_count, reported_count)
        if target is None or len(collected) >= target:
            return
        _raise_pubmed_search_truncated(
            self,
            reason="short_idlist",
            page_count=page_count,
            retstart=retstart,
            reported_count=reported_count,
            collected_count=len(collected),
            max_count=max_count,
        )

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


def _esearch_params(
    email: str,
    api_key: str | None,
    search_term: str,
    *,
    retstart: int,
    retmax: int,
) -> dict[str, str]:
    """Build an ESearch query. Omit ``retstart`` on the first page."""
    params = {
        "db": "pubmed",
        "term": search_term,
        "retmax": str(retmax),
    }
    if retstart > 0:
        params["retstart"] = str(retstart)
    params["usehistory"] = "y"
    params["retmode"] = "json"
    params["email"] = email
    if api_key and "your_" not in api_key:
        params["api_key"] = api_key
    return params


def _esearch_page_completes(
    collected: list[str],
    page_ids: list[str],
    max_count: int,
    reported_count: int | None,
) -> bool:
    """Stop when ``count`` is covered, or when the server sent no ``count``."""
    target = _esearch_target(max_count, reported_count)
    if target is None:
        return True
    return len(collected) + len(page_ids) >= target


def _append_completed_page(
    collected: list[str],
    page_ids: list[str],
    max_count: int,
    reported_count: int | None,
) -> None:
    """Append only the ids still required by ``count`` or ``max_count``."""
    target = _esearch_target(max_count, reported_count)
    if target is None:
        collected.extend(page_ids)
        return
    room = target - len(collected)
    if room > 0:
        collected.extend(page_ids[:room])


def _esearch_target(max_count: int, reported_count: int | None) -> int | None:
    """Return the id total this call must reach, or None when ``count`` is absent."""
    if reported_count is None:
        return None
    return min(max_count, max(reported_count, 0))


def _esearch_result_still_short(
    collected_count: int,
    max_count: int,
    reported_count: int | None,
) -> bool:
    """Return True while ``count`` is known and not yet covered."""
    target = _esearch_target(max_count, reported_count)
    return target is not None and collected_count < target


def _esearch_stall_reason(
    page_ids: list[str],
    seen_pages: set[tuple[str, ...]],
) -> str | None:
    """Classify a page that cannot move ``retstart`` toward ``count``."""
    if not page_ids:
        return "empty_page"
    if tuple(page_ids) in seen_pages:
        return "repeated_page"
    return None


def _parse_esearch_payload(payload: object) -> tuple[list[str], int | None]:
    """Read ``idlist`` and numeric ``count`` from an ESearch JSON object."""
    if not isinstance(payload, Mapping):
        return [], None
    result = payload.get("esearchresult")
    if not isinstance(result, Mapping):
        return [], None
    return (
        _parse_esearch_idlist(result.get("idlist")),
        _coerce_esearch_count(result.get("count")),
    )


def _parse_esearch_idlist(raw_ids: object) -> list[str]:
    """Normalize an ESearch id list to strings."""
    if not isinstance(raw_ids, list):
        return []
    return [str(item) for item in raw_ids if item is not None]


def _coerce_esearch_count(value: object) -> int | None:
    """Accept the integer ``count`` NCBI sends as a number or a decimal string."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def _raise_pubmed_search_truncated(
    host: PubMedSearchMixin,
    *,
    reason: str,
    page_count: int,
    retstart: int,
    reported_count: int | None,
    collected_count: int,
    max_count: int,
) -> None:
    """Log the incomplete ESearch scan and raise ``PaginationTruncatedError``."""
    raise_pagination_truncated(
        host._logger,
        event="pubmed_search_truncated",
        reason=reason,
        page_count=page_count,
        page_limit=_MAX_ESEARCH_PAGES,
        cursor_field="retstart",
        cursor_value=retstart,
        log_context={
            "count": reported_count,
            "collected": collected_count,
            "max_count": max_count,
        },
    )
