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
        while True:
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
            if next_offset is None or (limit and fetched >= limit):
                return
            current_offset = next_offset

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
        data_raw = response.json()
            import asyncio as _asyncio2
            if _asyncio2.iscoroutine(data_raw):
                data_raw = await data_raw
            data = data_raw
        return list(data.get("data", [])), data.get("next")
