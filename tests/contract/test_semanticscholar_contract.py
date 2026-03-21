"""Semantic Scholar API contract tests.

Verifies that the live Academic Graph search and batch endpoints remain
compatible with the current publication adapter expectations.
"""

from __future__ import annotations

import asyncio
from time import monotonic

import httpx
import pytest
import pytest_asyncio
from bioetl.domain.types import JsonDict

SEMANTICSCHOLAR_API_BASE = "https://api.semanticscholar.org/graph/v1"
STABLE_DOI = "10.1038/s41586-020-2649-2"
SEARCH_TITLE = "SARS-CoV-2"
SEARCH_FIELDS = "paperId,title,externalIds,year"
REQUEST_SPACING_SECONDS = 1.25
RATE_LIMIT_RETRY_SECONDS = 2.0
pytestmark = pytest.mark.network
_LAST_REQUEST_AT = 0.0
_SEARCH_PAYLOAD_CACHE: JsonDict | None = None
_BATCH_PAYLOAD_CACHE: list[JsonDict | None] | None = None
_HEALTH_PAYLOAD_CACHE: JsonDict | None = None


async def _respect_request_spacing() -> None:
    """Throttle live requests to stay under the public API rate limit."""
    global _LAST_REQUEST_AT
    elapsed = monotonic() - _LAST_REQUEST_AT
    if elapsed < REQUEST_SPACING_SECONDS:
        await asyncio.sleep(REQUEST_SPACING_SECONDS - elapsed)


async def _request_or_skip(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: object,
) -> httpx.Response:
    """Execute request and skip on transient network/provider outages."""
    global _LAST_REQUEST_AT
    for attempt in range(2):
        await _respect_request_spacing()
        try:
            response = await client.request(method, url, **kwargs)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            pytest.skip(f"Semantic Scholar endpoint not reachable: {exc}")

        _LAST_REQUEST_AT = monotonic()
        if response.status_code == 429 and attempt == 0:
            await asyncio.sleep(RATE_LIMIT_RETRY_SECONDS)
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
            headers={"Accept": "application/json"},
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


@pytest_asyncio.fixture
async def semanticscholar_health_payload(
    semanticscholar_client: httpx.AsyncClient,
) -> JsonDict:
    """Cached low-cost health-style search response."""
    global _HEALTH_PAYLOAD_CACHE
    if _HEALTH_PAYLOAD_CACHE is None:
        response = await _request_or_skip(
            semanticscholar_client,
            "GET",
            f"{SEMANTICSCHOLAR_API_BASE}/paper/search",
            params={
                "query": "*",
                "limit": 1,
                "offset": 0,
                "fields": "paperId,title",
            },
            headers={"Accept": "application/json"},
        )
        _HEALTH_PAYLOAD_CACHE = response.json()
    return _HEALTH_PAYLOAD_CACHE


@pytest.mark.semanticscholar
class TestSemanticScholarContract:
    """Contract tests for Semantic Scholar live publication API behavior."""

    @pytest.mark.asyncio
    async def test_paper_search_endpoint(
        self,
        semanticscholar_search_payload: JsonDict,
    ) -> None:
        """Verify free-text search remains available with paginated shape."""
        data = semanticscholar_search_payload
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1
        assert "total" in data

    @pytest.mark.asyncio
    async def test_paper_batch_lookup_by_doi(
        self,
        semanticscholar_batch_payload: list[JsonDict | None],
    ) -> None:
        """Verify DOI batch lookup returns a paper-compatible record."""
        data = semanticscholar_batch_payload
        assert isinstance(data, list)
        assert len(data) == 1
        paper = data[0]
        assert isinstance(paper, dict)
        assert paper["paperId"]
        assert paper["title"]
        assert "externalIds" in paper

    @pytest.mark.asyncio
    async def test_batch_lookup_preserves_doi_identity(
        self,
        semanticscholar_batch_payload: list[JsonDict | None],
    ) -> None:
        """Verify batch lookup still surfaces DOI identity metadata."""
        data = semanticscholar_batch_payload
        paper = data[0]
        external_ids = paper.get("externalIds", {})
        assert isinstance(external_ids, dict)
        assert external_ids.get("DOI", "").lower() == STABLE_DOI.lower()

    @pytest.mark.asyncio
    async def test_health_probe_shape(
        self,
        semanticscholar_health_payload: JsonDict,
    ) -> None:
        """Verify minimal health-style search request remains successful."""
        data = semanticscholar_health_payload
        assert "data" in data
        assert isinstance(data["data"], list)
        assert "total" in data
