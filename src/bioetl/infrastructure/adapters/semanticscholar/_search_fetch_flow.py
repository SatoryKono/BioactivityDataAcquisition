# mypy: disable-error-code=attr-defined
# Host attrs/methods provided by concrete composition.
"""Internal search pagination helpers for Semantic Scholar fetch flow."""

from __future__ import annotations

__all__ = ["_SemanticScholarSearchFetchMixin"]

import contextlib
import time
from typing import TYPE_CHECKING, Any, Protocol

from bioetl.domain.types import BronzeRecord, JsonDict
from bioetl.infrastructure.adapters.semanticscholar.constants import (
    SEMANTICSCHOLAR_BASE_URL,
)
from bioetl.domain.mixin_host import as_mixin_host

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
        current_offset = 0
        page_size = min(100, limit or 100)
        fetched = 0
        while True:
            records, next_offset = await as_mixin_host(self)._fetch_search_page(  # Any: mixin host surface (self attrs/methods)
                query=query,
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
        params: JsonDict = {
            "query": query or "*",
            "fields": as_mixin_host(self).fields,  # Any: mixin host surface (self attrs/methods)
            "offset": current_offset,
            "limit": page_size,
        }
        url = f"{SEMANTICSCHOLAR_BASE_URL}/paper/search"
        start_time = time.perf_counter()
        with as_mixin_host(self)._adapter_metrics.measure_request("/paper/search"):  # Any: mixin host surface (self attrs/methods)
            response = await as_mixin_host(self)._http_client.get_once(  # Any: mixin host surface (self attrs/methods)
                url, params=params, headers=as_mixin_host(self)._build_headers()  # Any: mixin host surface (self attrs/methods)
            )
        duration_ms = (time.perf_counter() - start_time) * 1000
        with contextlib.suppress(Exception):
            as_mixin_host(self)._request_collector.record_from_response(response, duration_ms)  # Any: mixin host surface (self attrs/methods)
        data = response.json()
        return list(data.get("data", [])), data.get("next")
