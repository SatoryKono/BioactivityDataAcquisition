# mypy: disable-error-code=attr-defined
# Host attrs/methods provided by concrete composition.
"""Internal search pagination helpers for Semantic Scholar fetch flow."""

from __future__ import annotations

__all__ = ["_SemanticScholarSearchFetchMixin"]

import contextlib
import time
from typing import TYPE_CHECKING

import datetime
import httpx
from email.utils import parsedate_to_datetime

from bioetl.domain.exceptions import RetryExhaustedError
from bioetl.domain.exceptions.network.service import ApiError
from bioetl.domain.mixin_host import as_mixin_host
from bioetl.domain.types import BronzeRecord, JsonDict
from bioetl.infrastructure.adapters.semanticscholar.constants import (
    SEMANTICSCHOLAR_BASE_URL,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator



def _extract_retry_after_seconds(response: httpx.Response | None) -> float | None:
    if response is None:
        return None
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(raw)
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = (dt - now).total_seconds()
        return max(0.0, delta)
    except Exception:
        return None

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
            records, next_offset = await as_mixin_host(
                self
            )._fetch_search_page(  # Any: mixin host
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
        if query is None or not query.strip():
            raise ValueError("Semantic Scholar search requires explicit query; use filter_ids for batch lookup")
        params: JsonDict = {
            "query": query,
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
                )._http_client.get(  # Any: mixin host - bounded retry for 429 via UnifiedHTTPClient
                    url,
                    params=params,
                    headers=as_mixin_host(self)._build_headers(),  # Any: mixin host
                )
            except RetryExhaustedError as exc:
                last_resp = None
                if exc.last_error is not None and hasattr(exc.last_error, "response"):
                    try:
                        last_resp = exc.last_error.response  # type: ignore[attr-defined]
                    except Exception:
                        last_resp = None
                retry_after = _extract_retry_after_seconds(last_resp)
                msg = f"Semantic Scholar search failed: 429 {url}"
                if retry_after is not None:
                    msg += f" Retry-After={retry_after:.1f}s"
                raise ApiError(
                    msg,
                    status_code=429,
                ) from exc
            except httpx.HTTPStatusError as exc:
                retry_after = _extract_retry_after_seconds(exc.response)
                msg = f"Semantic Scholar search failed: {exc.response.status_code} {url}"
                if retry_after is not None:
                    msg += f" Retry-After={retry_after:.1f}s"
                raise ApiError(
                    msg,
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
