"""OpenAlex API contract tests.

Verifies that OpenAlex `/works` endpoint semantics and response schemas remain
compatible with the current publication adapter expectations.
"""

from __future__ import annotations

import os

import httpx
import pytest

from tests.contract._provider_contract_drift import (
    assert_provider_probe_matches_snapshot,
)

OPENALEX_API_BASE = "https://api.openalex.org"
OPENALEX_MAILTO = "bioetl-test@example.com"
STABLE_DOI = "10.1038/s41586-020-2649-2"
SEARCH_TITLE = "SARS-CoV-2"
UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"
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
        pytest.skip(f"OpenAlex endpoint not reachable: {exc}")

    if response.status_code in {429, 502, 503, 504}:
        pytest.skip(f"OpenAlex temporary server error: HTTP {response.status_code}")
    return response


@pytest.mark.openalex
class TestOpenAlexContract:
    """Contract tests for OpenAlex live publication API behavior."""

    @pytest.mark.asyncio
    async def test_works_filter_by_doi(self) -> None:
        """Verify DOI filter lookup returns at least one work."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{OPENALEX_API_BASE}/works",
                params={
                    "mailto": OPENALEX_MAILTO,
                    "filter": f"doi:{STABLE_DOI}",
                    "per-page": 1,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)
        assert len(data["results"]) >= 1

        work = data["results"][0]
        assert "id" in work
        assert "doi" in work
        assert work["doi"]

    @pytest.mark.asyncio
    async def test_works_search_endpoint(self) -> None:
        """Verify free-text search remains available."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{OPENALEX_API_BASE}/works",
                params={
                    "mailto": OPENALEX_MAILTO,
                    "search": SEARCH_TITLE,
                    "per-page": 1,
                    "cursor": "*",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)
        assert len(data["results"]) >= 1

    @pytest.mark.asyncio
    async def test_title_search_filter(self) -> None:
        """Verify title.search filter remains accepted by the API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{OPENALEX_API_BASE}/works",
                params={
                    "mailto": OPENALEX_MAILTO,
                    "filter": f"title.search:{SEARCH_TITLE}",
                    "per-page": 1,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    @pytest.mark.asyncio
    async def test_health_probe_shape(self) -> None:
        """Verify minimal health-style request remains successful."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{OPENALEX_API_BASE}/works",
                params={
                    "mailto": OPENALEX_MAILTO,
                    "per-page": 1,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "meta" in data

    @pytest.mark.asyncio
    async def test_works_filter_snapshot_contract(self) -> None:
        """Verify the provider-facing DOI filter payload matches the snapshot."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{OPENALEX_API_BASE}/works",
                params={
                    "mailto": OPENALEX_MAILTO,
                    "filter": f"doi:{STABLE_DOI}",
                    "per-page": 1,
                },
            )

        assert response.status_code == 200
        assert_provider_probe_matches_snapshot(
            "openalex",
            "works_filter_by_doi",
            response.json(),
            update_snapshots=UPDATE_SNAPSHOTS,
        )

    @pytest.mark.asyncio
    async def test_works_search_snapshot_contract(self) -> None:
        """Verify the provider-facing search payload matches the snapshot."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{OPENALEX_API_BASE}/works",
                params={
                    "mailto": OPENALEX_MAILTO,
                    "search": SEARCH_TITLE,
                    "per-page": 1,
                    "cursor": "*",
                },
            )

        assert response.status_code == 200
        assert_provider_probe_matches_snapshot(
            "openalex",
            "works_search_endpoint",
            response.json(),
            update_snapshots=UPDATE_SNAPSHOTS,
        )

    @pytest.mark.asyncio
    async def test_health_probe_snapshot_contract(self) -> None:
        """Verify the provider-facing health payload matches the snapshot."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{OPENALEX_API_BASE}/works",
                params={
                    "mailto": OPENALEX_MAILTO,
                    "per-page": 1,
                },
            )

        assert response.status_code == 200
        assert_provider_probe_matches_snapshot(
            "openalex",
            "health_probe_shape",
            response.json(),
            update_snapshots=UPDATE_SNAPSHOTS,
        )
