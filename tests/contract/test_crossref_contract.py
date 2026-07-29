# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Crossref API contract tests.

Verifies that Crossref REST API endpoints and response schemas haven't changed.
These tests make live API calls and require BIOETL_LIVE_API_TESTS=true.
"""

from __future__ import annotations

import os
from urllib.parse import quote

import httpx
import pytest

from tests.contract._provider_contract_drift import (
    assert_provider_probe_matches_snapshot,
)

CROSSREF_API_BASE = "https://api.crossref.org"
STABLE_DOI = "10.1038/s41586-020-2649-2"
SEARCH_TITLE = "SARS-CoV-2"
UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"
TRANSIENT_PROVIDER_STATUSES = {429, 500, 502, 503, 504}
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
        pytest.skip(f"Crossref endpoint not reachable: {exc}")

    if response.status_code in TRANSIENT_PROVIDER_STATUSES:
        pytest.skip(f"Crossref temporary server error: HTTP {response.status_code}")
    return response


@pytest.mark.crossref
class TestCrossrefContract:
    """Contract tests for Crossref REST API."""

    @pytest.mark.asyncio
    async def test_work_lookup_by_doi(self) -> None:
        """Verify direct DOI lookup returns a work record."""
        encoded_doi = quote(STABLE_DOI, safe="")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{CROSSREF_API_BASE}/works/{encoded_doi}",
                headers={"Accept": "application/json"},
            )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        message = data["message"]
        assert message["DOI"].lower() == STABLE_DOI.lower()
        assert "title" in message
        assert isinstance(message["title"], list)
        assert message["title"]

    @pytest.mark.asyncio
    async def test_works_query_endpoint(self) -> None:
        """Verify query search returns paginated items."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{CROSSREF_API_BASE}/works",
                params={"query.title": SEARCH_TITLE, "rows": 1},
                headers={"Accept": "application/json"},
            )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        message = data["message"]
        assert "items" in message
        assert isinstance(message["items"], list)
        assert len(message["items"]) >= 1

    @pytest.mark.asyncio
    async def test_member_endpoint(self) -> None:
        """Verify member lookup endpoint remains available."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{CROSSREF_API_BASE}/members/311",
                headers={"Accept": "application/json"},
            )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert "message" in data
        assert data["message"]["id"] == 311

    @pytest.mark.asyncio
    async def test_agency_lookup_for_doi(self) -> None:
        """Verify agency lookup for a known DOI stays available."""
        encoded_doi = quote(STABLE_DOI, safe="")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{CROSSREF_API_BASE}/works/{encoded_doi}/agency",
                headers={"Accept": "application/json"},
            )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert "message" in data
        assert data["message"]["DOI"].lower() == STABLE_DOI.lower()
        assert data["message"]["agency"]["id"].lower() == "crossref"

    @pytest.mark.asyncio
    async def test_work_lookup_snapshot_contract(self) -> None:
        """Verify the provider-facing DOI lookup payload matches the snapshot."""
        encoded_doi = quote(STABLE_DOI, safe="")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{CROSSREF_API_BASE}/works/{encoded_doi}",
                headers={"Accept": "application/json"},
            )

        assert response.status_code == 200
        assert_provider_probe_matches_snapshot(
            "crossref",
            "work_lookup_by_doi",
            response.json(),
            update_snapshots=UPDATE_SNAPSHOTS,
        )

    @pytest.mark.asyncio
    async def test_works_query_snapshot_contract(self) -> None:
        """Verify the provider-facing search payload matches the snapshot."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{CROSSREF_API_BASE}/works",
                params={"query.title": SEARCH_TITLE, "rows": 1},
                headers={"Accept": "application/json"},
            )

        assert response.status_code == 200
        assert_provider_probe_matches_snapshot(
            "crossref",
            "works_query_endpoint",
            response.json(),
            update_snapshots=UPDATE_SNAPSHOTS,
        )

    @pytest.mark.asyncio
    async def test_agency_lookup_snapshot_contract(self) -> None:
        """Verify the provider-facing agency payload matches the snapshot."""
        encoded_doi = quote(STABLE_DOI, safe="")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{CROSSREF_API_BASE}/works/{encoded_doi}/agency",
                headers={"Accept": "application/json"},
            )

        assert response.status_code == 200
        assert_provider_probe_matches_snapshot(
            "crossref",
            "agency_lookup_for_doi",
            response.json(),
            update_snapshots=UPDATE_SNAPSHOTS,
        )
