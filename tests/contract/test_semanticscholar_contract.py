"""Semantic Scholar API contract tests.

Verifies that the live Academic Graph search and batch endpoints remain
compatible with the current publication adapter expectations.
"""

from __future__ import annotations

import httpx
import pytest

SEMANTICSCHOLAR_API_BASE = "https://api.semanticscholar.org/graph/v1"
STABLE_DOI = "10.1038/s41586-020-2649-2"
SEARCH_TITLE = "SARS-CoV-2"
SEARCH_FIELDS = "paperId,title,externalIds,year"
pytestmark = pytest.mark.network


async def _request_or_skip(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: object,
) -> httpx.Response:
    """Execute request and skip on transient network/provider outages."""
    try:
        response = await client.request(method, url, **kwargs)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        pytest.skip(f"Semantic Scholar endpoint not reachable: {exc}")

    if response.status_code in {429, 502, 503, 504}:
        pytest.skip(
            f"Semantic Scholar temporary server error: HTTP {response.status_code}"
        )
    return response


@pytest.mark.semanticscholar
class TestSemanticScholarContract:
    """Contract tests for Semantic Scholar live publication API behavior."""

    @pytest.mark.asyncio
    async def test_paper_search_endpoint(self) -> None:
        """Verify free-text search remains available with paginated shape."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
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

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1
        assert "total" in data

    @pytest.mark.asyncio
    async def test_paper_batch_lookup_by_doi(self) -> None:
        """Verify DOI batch lookup returns a paper-compatible record."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "POST",
                f"{SEMANTICSCHOLAR_API_BASE}/paper/batch",
                params={"fields": SEARCH_FIELDS},
                json={"ids": [f"DOI:{STABLE_DOI}"]},
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        paper = data[0]
        assert isinstance(paper, dict)
        assert paper["paperId"]
        assert paper["title"]
        assert "externalIds" in paper

    @pytest.mark.asyncio
    async def test_batch_lookup_preserves_doi_identity(self) -> None:
        """Verify batch lookup still surfaces DOI identity metadata."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "POST",
                f"{SEMANTICSCHOLAR_API_BASE}/paper/batch",
                params={"fields": SEARCH_FIELDS},
                json={"ids": [f"DOI:{STABLE_DOI}"]},
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )

        assert response.status_code == 200
        data = response.json()
        paper = data[0]
        external_ids = paper.get("externalIds", {})
        assert isinstance(external_ids, dict)
        assert external_ids.get("DOI", "").lower() == STABLE_DOI.lower()

    @pytest.mark.asyncio
    async def test_health_probe_shape(self) -> None:
        """Verify minimal health-style search request remains successful."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
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

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        assert "total" in data
