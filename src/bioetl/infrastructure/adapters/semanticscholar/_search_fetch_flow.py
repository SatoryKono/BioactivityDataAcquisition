# mypy: disable-error-code=attr-defined
# Host attrs/methods provided by concrete composition.
"""Internal search pagination helpers for Semantic Scholar fetch flow."""

from __future__ import annotations

__all__ = ["_SemanticScholarSearchFetchMixin"]

import contextlib
import time
from typing import TYPE_CHECKING

import httpx

from bioetl.domain.exceptions.network.service import ApiError
from bioetl.domain.mixin_host import as_mixin_host
from bioetl.domain.types import BronzeRecord, JsonDict
from bioetl.infrastructure.adapters.semanticscholar.constants import (
    SEMANTICSCHOLAR_BASE_URL,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

# Hard ceiling against runaway offset loops from misbehaving providers (CF-034).
_DEFAULT_MAX_PAGES: int = 10_000


class _SemanticScholarSearchFetchMixin:
    """Search/page flow helpers kept separate from DOI/fallback paths."""

    async def _paginate_search(
        self,
        *,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Paginate through search results with optional limit."""
        search_query = self._require_search_query(query)
        current_offset = 0
        page_size = min(100, limit or 100)
        fetched = 0
        page_count = 0
        seen_offsets: set[int] = set()
        while True:
            if page_count >= _DEFAULT_MAX_PAGES:
                as_mixin_host(self)._logger.warning(  # Any: mixin host
                    "semanticscholar_search_truncated",
                    reason="max_pages",
                    query=search_query[:100],
                    page_count=page_count,
                    page_limit=_DEFAULT_MAX_PAGES,
                    next_offset=current_offset,
                )
                return
            page_count += 1
            records, next_offset = await as_mixin_host(
                self
            )._fetch_search_page(  # Any: mixin host
                query=search_query,
                page_size=page_size,
                current_offset=current_offset,
            )
            for record in records:
                if limit and fetched >= limit:
                    return
                yield record
                fetched += 1
            if not self._search_pagination_has_next(
                next_offset=next_offset,
                current_offset=current_offset,
                seen_offsets=seen_offsets,
                fetched=fetched,
                limit=limit,
                query=search_query,
                page_count=page_count,
            ):
                return
            assert next_offset is not None
            seen_offsets.add(current_offset)
            current_offset = next_offset

    def _search_pagination_has_next(
        self,
        *,
        next_offset: int | None,
        current_offset: int,
        seen_offsets: set[int],
        fetched: int,
        limit: int | None,
        query: str,
        page_count: int,
    ) -> bool:
        """Distinguish normal exhaustion/limit completion from repeated offsets."""
        if next_offset is None or (limit and fetched >= limit):
            return False
        if next_offset in seen_offsets or next_offset == current_offset:
            as_mixin_host(self)._logger.warning(
                "semanticscholar_search_truncated",
                reason="repeated_offset",
                query=query[:100],
                page_count=page_count,
                page_limit=_DEFAULT_MAX_PAGES,
                next_offset=next_offset,
            )
            return False
        return True

    @staticmethod
    def _require_search_query(query: str | None) -> str:
        """Return a normalized non-empty search query."""
        if query is None or not query.strip():
            raise ValueError("Semantic Scholar search query must be non-empty")
        return query.strip()

    @staticmethod
    def _validate_entity_type(entity_type: str) -> None:
        """Validate supported Semantic Scholar entity types."""
        if entity_type in ("publication", "paper"):
            return
        raise ValueError(
            "SemanticScholarAdapter supports 'publication' or 'paper', "
            f"got: {entity_type}"
        )

    async def _fetch_search_page(
        self,
        *,
        query: str | None,
        page_size: int,
        current_offset: int,
    ) -> tuple[list[BronzeRecord], int | None]:
        """Fetch one search page and emit request telemetry."""
        search_query = self._require_search_query(query)
        params: JsonDict = {
            "query": search_query,
            "fields": as_mixin_host(self).fields,  # Any: mixin host
            "offset": current_offset,
            "limit": page_size,
        }
        url = f"{SEMANTICSCHOLAR_BASE_URL}/paper/search"
        start_time = time.perf_counter()
        with as_mixin_host(self)._adapter_metrics.measure_request(
            "/paper/search"
        ):  # Any: mixin host
            try:
                response = await as_mixin_host(
                    self
                )._http_client.get(  # Any: mixin host
                    url,
                    params=params,
                    headers=as_mixin_host(self)._build_headers(),  # Any: mixin host
                )
            except httpx.HTTPStatusError as exc:
                raise ApiError(
                    "Semantic Scholar search request failed",
                    status_code=exc.response.status_code,
                ) from exc
            except httpx.RequestError as exc:
                raise ApiError("Semantic Scholar search transport failed") from exc
        duration_ms = (time.perf_counter() - start_time) * 1000
        with contextlib.suppress(Exception):
            as_mixin_host(self)._request_collector.record_from_response(
                response, duration_ms
            )  # Any: mixin host
        data = response.json()
        return list(data.get("data", [])), data.get("next")
