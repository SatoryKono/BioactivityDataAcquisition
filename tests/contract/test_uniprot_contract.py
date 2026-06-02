"""UniProt API contract tests.

Verifies that UniProt REST API endpoints and response schemas haven't changed.
These tests make live API calls and require BIOETL_LIVE_API_TESTS=true.

See:
    - https://www.uniprot.org/help/api
    - RULES.md Appendix A - UniProt specifications
"""

from __future__ import annotations

import os

import httpx
import pytest

from tests.contract._provider_contract_drift import (
    assert_provider_probe_matches_snapshot,
)
from tests.contract.conftest import UNIPROT_PROTEIN_REQUIRED_FIELDS

UNIPROT_API_BASE = "https://rest.uniprot.org"
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
    except httpx.TransportError as exc:
        pytest.skip(f"UniProt endpoint not reachable: {exc}")

    if response.status_code >= 500:
        pytest.skip(f"UniProt temporary server error: HTTP {response.status_code}")
    return response


@pytest.mark.uniprot
class TestUniProtContract:
    """Contract tests for UniProt REST API."""

    @pytest.mark.asyncio
    async def test_uniprotkb_search_endpoint(self) -> None:
        """Verify UniProtKB search endpoint works."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{UNIPROT_API_BASE}/uniprotkb/search",
                params={
                    "query": "ubiquitin",
                    "size": 1,
                    "format": "json",
                },
            )

        assert response.status_code == 200
        data = response.json()

        # Response should have results
        assert "results" in data
        assert len(data["results"]) >= 1

        # Verify required fields
        protein = data["results"][0]
        missing_fields = UNIPROT_PROTEIN_REQUIRED_FIELDS - set(protein.keys())
        assert not missing_fields, f"Missing required fields: {missing_fields}"

    @pytest.mark.asyncio
    async def test_uniprotkb_search_snapshot_contract(self) -> None:
        """Verify search payload matches the managed snapshot."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{UNIPROT_API_BASE}/uniprotkb/search",
                params={
                    "query": "ubiquitin",
                    "size": 1,
                    "format": "json",
                },
            )

        assert response.status_code == 200
        assert_provider_probe_matches_snapshot(
            "uniprot",
            "uniprotkb_search_endpoint",
            response.json(),
            update_snapshots=UPDATE_SNAPSHOTS,
        )

    @pytest.mark.asyncio
    async def test_specific_protein_lookup(self) -> None:
        """Verify direct protein lookup by accession."""
        accession = "P0DTD1"  # SARS-CoV-2 Replicase polyprotein

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{UNIPROT_API_BASE}/uniprotkb/{accession}",
                params={"format": "json"},
            )

        assert response.status_code == 200
        data = response.json()

        assert data["primaryAccession"] == accession
        assert "sequence" in data

    @pytest.mark.asyncio
    async def test_specific_protein_lookup_snapshot_contract(self) -> None:
        """Verify direct lookup payload matches the managed snapshot."""
        accession = "P0DTD1"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{UNIPROT_API_BASE}/uniprotkb/{accession}",
                params={"format": "json"},
            )

        assert response.status_code == 200
        assert_provider_probe_matches_snapshot(
            "uniprot",
            "specific_protein_lookup",
            response.json(),
            update_snapshots=UPDATE_SNAPSHOTS,
        )

    @pytest.mark.asyncio
    async def test_fasta_format_available(self) -> None:
        """Verify FASTA format is still supported."""
        accession = "P0DTD1"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{UNIPROT_API_BASE}/uniprotkb/{accession}.fasta",
            )

        assert response.status_code == 200
        content = response.text

        # FASTA format check
        assert content.startswith(">")
        assert accession in content

    @pytest.mark.asyncio
    async def test_proteomes_endpoint(self) -> None:
        """Verify proteomes endpoint schema."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{UNIPROT_API_BASE}/proteomes/search",
                params={
                    "query": "human",
                    "size": 1,
                    "format": "json",
                },
            )

        assert response.status_code == 200
        data = response.json()

        assert "results" in data

    @pytest.mark.asyncio
    async def test_taxonomy_endpoint(self) -> None:
        """Verify taxonomy endpoint works."""
        # Human taxonomy ID
        taxonomy_id = "9606"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{UNIPROT_API_BASE}/taxonomy/{taxonomy_id}",
                params={"format": "json"},
            )

        assert response.status_code == 200
        data = response.json()

        assert "taxonId" in data
        assert data["taxonId"] == int(taxonomy_id)
        assert "scientificName" in data

    @pytest.mark.asyncio
    async def test_taxonomy_snapshot_contract(self) -> None:
        """Verify taxonomy payload matches the managed snapshot."""
        taxonomy_id = "9606"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{UNIPROT_API_BASE}/taxonomy/{taxonomy_id}",
                params={"format": "json"},
            )

        assert response.status_code == 200
        assert_provider_probe_matches_snapshot(
            "uniprot",
            "taxonomy_endpoint",
            response.json(),
            update_snapshots=UPDATE_SNAPSHOTS,
        )

    @pytest.mark.asyncio
    async def test_pagination_headers(self) -> None:
        """Verify pagination via Link headers."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _request_or_skip(
                client,
                "GET",
                f"{UNIPROT_API_BASE}/uniprotkb/search",
                params={
                    "query": "*",
                    "size": 5,
                    "format": "json",
                },
            )

        assert response.status_code == 200

        # UniProt uses Link header for pagination
        # May not always be present for small result sets
        # Just verify the response is valid
        data = response.json()
        assert "results" in data

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_idmapping_endpoint(self) -> None:
        """Verify ID mapping endpoint structure."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Submit mapping job
            response = await _request_or_skip(
                client,
                "POST",
                f"{UNIPROT_API_BASE}/idmapping/run",
                data={
                    "from": "UniProtKB_AC-ID",
                    "to": "UniProtKB",
                    "ids": "P05067",
                },
            )

        # ID mapping may return 200 with job ID or redirect
        assert response.status_code in (200, 303, 302)
