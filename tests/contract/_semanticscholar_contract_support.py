"""Shared support for Semantic Scholar live contract tests."""

from __future__ import annotations

import asyncio
import contextlib
from time import monotonic

import httpx
import pytest
import pytest_asyncio
from bioetl.domain.types import JsonDict

SEMANTICSCHOLAR_API_BASE = "https://api.semanticscholar.org/graph/v1"
STABLE_DOI = "10.1038/s41586-020-2649-2"
SEARCH_TITLE = "SARS-CoV-2"
SEARCH_FIELDS = "paperId,title,externalIds,year"
JSON_ACCEPT_HEADER = "application/json"
REQUEST_SPACING_SECONDS = 4.0
RATE_LIMIT_RETRY_SECONDS = 4.0
MAX_RATE_LIMIT_ATTEMPTS = 4
pytestmark = pytest.mark.network
_LAST_REQUEST_AT = 0.0
_SEARCH_PAYLOAD_CACHE: JsonDict | None = None
_BATCH_PAYLOAD_CACHE: list[JsonDict | None] | None = None


async def _respect_request_spacing() -> None:
    """Throttle live requests to stay under the public API rate limit."""
    global _LAST_REQUEST_AT
    elapsed = monotonic() - _LAST_REQUEST_AT
    if elapsed < REQUEST_SPACING_SECONDS:
        await asyncio.sleep(REQUEST_SPACING_SECONDS - elapsed)


def _retry_after_seconds(response: httpx.Response) -> float:
    """Return retry delay from headers, falling back to default backoff."""
    raw_retry_after = response.headers.get("Retry-After", "").strip()
    if raw_retry_after:
        with contextlib.suppress(ValueError):
            parsed = float(raw_retry_after)
            if parsed > 0:
                return parsed
    return RATE_LIMIT_RETRY_SECONDS


def _backoff_seconds(response: httpx.Response, attempt: int) -> float:
    """Increase waiting time across repeated rate-limit responses."""
    base_delay = _retry_after_seconds(response)
    multiplier = max(1, attempt + 1)
    return base_delay * multiplier


async def _request_or_skip(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: object,
) -> httpx.Response:
    """Execute request and skip on transient network/provider outages."""
    global _LAST_REQUEST_AT
    for attempt in range(MAX_RATE_LIMIT_ATTEMPTS):
        await _respect_request_spacing()
        try:
            response = await client.request(method, url, **kwargs)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            pytest.skip(f"Semantic Scholar endpoint not reachable: {exc}")

        _LAST_REQUEST_AT = monotonic()
        if response.status_code == 429 and attempt < (MAX_RATE_LIMIT_ATTEMPTS - 1):
            await asyncio.sleep(_backoff_seconds(response, attempt))
            continue
        if response.status_code in {429, 502, 503, 504}:
            pytest.skip(
                f"Semantic Scholar temporary server error: HTTP {response.status_code}"
            )
        return response

    pytest.skip("Semantic Scholar temporary server error: exhausted 429 retry budget")


@pytest_asyncio.fixture
async def semanticscholar_client() -> httpx.AsyncClient:
    """Shared AsyncClient to avoid needless connection churn in live runs."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def semanticscholar_search_payload(
    semanticscholar_client: httpx.AsyncClient,
) -> JsonDict:
    """Cached free-text search response for shape assertions."""
    global _SEARCH_PAYLOAD_CACHE
    if _SEARCH_PAYLOAD_CACHE is None:
        response = await _request_or_skip(
            semanticscholar_client,
            "GET",
            f"{SEMANTICSCHOLAR_API_BASE}/paper/search",
            params={
                "query": SEARCH_TITLE,
                "limit": 1,
                "offset": 0,
                "fields": SEARCH_FIELDS,
            },
            headers={"Accept": JSON_ACCEPT_HEADER},
        )
        _SEARCH_PAYLOAD_CACHE = response.json()
    return _SEARCH_PAYLOAD_CACHE


@pytest_asyncio.fixture
async def semanticscholar_batch_payload(
    semanticscholar_client: httpx.AsyncClient,
) -> list[JsonDict | None]:
    """Cached DOI batch lookup response reused across batch assertions."""
    global _BATCH_PAYLOAD_CACHE
    if _BATCH_PAYLOAD_CACHE is None:
        response = await _request_or_skip(
            semanticscholar_client,
            "POST",
            f"{SEMANTICSCHOLAR_API_BASE}/paper/batch",
            params={"fields": SEARCH_FIELDS},
            json={"ids": [f"DOI:{STABLE_DOI}"]},
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        _BATCH_PAYLOAD_CACHE = response.json()
    return _BATCH_PAYLOAD_CACHE
