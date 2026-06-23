"""PubMed API contract tests.

Verifies that NCBI E-utilities API endpoints and response schemas haven't changed.
These tests make live API calls and require BIOETL_LIVE_API_TESTS=true.

See:
    - https://www.ncbi.nlm.nih.gov/books/NBK25500/
    - RULES.md Appendix A - PubMed specifications
"""

from __future__ import annotations

import os

import httpx
import pytest

from tests.contract._provider_contract_drift import (
    assert_provider_probe_matches_snapshot,
)

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
STABLE_PMID = "33408181"
UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"
pytestmark = pytest.mark.network


@pytest.mark.pubmed
class TestPubMedContract:
    """Contract tests for NCBI E-utilities (PubMed) API."""

    @pytest.mark.asyncio
    async def test_esearch_endpoint(self) -> None:
        """Verify ESearch endpoint for searching PubMed."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{EUTILS_BASE}/esearch.fcgi",
                params={
                    "db": "pubmed",
                    "term": "cancer",
                    "retmax": 5,
                    "retmode": "json",
                },
            )

        assert response.status_code == 200
        data = response.json()

        assert "esearchresult" in data
        result = data["esearchresult"]

        # Required fields in search result
        assert "count" in result
        assert "idlist" in result
        assert len(result["idlist"]) <= 5

    @pytest.mark.asyncio
    async def test_efetch_endpoint(self) -> None:
        """Verify EFetch endpoint for retrieving records."""
        pmid = STABLE_PMID  # Known stable PMID

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{EUTILS_BASE}/efetch.fcgi",
                params={
                    "db": "pubmed",
                    "id": pmid,
                    "retmode": "xml",
                },
            )

        assert response.status_code == 200
        content = response.text

        # Should return XML with article data
        assert "PubmedArticle" in content or "PubmedArticleSet" in content

    @pytest.mark.asyncio
    async def test_esummary_endpoint(self) -> None:
        """Verify ESummary endpoint for document summaries."""
        pmid = STABLE_PMID

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{EUTILS_BASE}/esummary.fcgi",
                params={
                    "db": "pubmed",
                    "id": pmid,
                    "retmode": "json",
                },
            )

        assert response.status_code == 200
        data = response.json()

        assert "result" in data
        result = data["result"]

        # Should have the PMID as key
        assert pmid in result
        article = result[pmid]

        # Required summary fields
        assert "title" in article
        assert "pubdate" in article

    @pytest.mark.asyncio
    async def test_einfo_database_list(self) -> None:
        """Verify EInfo returns database information."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{EUTILS_BASE}/einfo.fcgi",
                params={"retmode": "json"},
            )

        assert response.status_code == 200
        data = response.json()

        assert "einforesult" in data
        assert "dblist" in data["einforesult"]

        # PubMed should be in the list
        assert "pubmed" in data["einforesult"]["dblist"]

    @pytest.mark.asyncio
    async def test_esearch_snapshot_contract(self) -> None:
        """Verify the provider-facing ESearch payload matches the snapshot."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{EUTILS_BASE}/esearch.fcgi",
                params={
                    "db": "pubmed",
                    "term": "cancer",
                    "retmax": 5,
                    "retmode": "json",
                },
            )

        assert response.status_code == 200
        assert_provider_probe_matches_snapshot(
            "pubmed",
            "esearch_endpoint",
            response.json(),
            update_snapshots=UPDATE_SNAPSHOTS,
        )

    @pytest.mark.asyncio
    async def test_esummary_snapshot_contract(self) -> None:
        """Verify the provider-facing ESummary payload matches the snapshot."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{EUTILS_BASE}/esummary.fcgi",
                params={
                    "db": "pubmed",
                    "id": STABLE_PMID,
                    "retmode": "json",
                },
            )

        assert response.status_code == 200
        assert_provider_probe_matches_snapshot(
            "pubmed",
            "esummary_endpoint",
            response.json(),
            update_snapshots=UPDATE_SNAPSHOTS,
        )

    @pytest.mark.asyncio
    async def test_einfo_database_list_snapshot_contract(self) -> None:
        """Verify the provider-facing EInfo database list payload matches the snapshot."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{EUTILS_BASE}/einfo.fcgi",
                params={"retmode": "json"},
            )

        assert response.status_code == 200
        assert_provider_probe_matches_snapshot(
            "pubmed",
            "einfo_database_list",
            response.json(),
            update_snapshots=UPDATE_SNAPSHOTS,
        )

    @pytest.mark.asyncio
    async def test_einfo_pubmed_details(self) -> None:
        """Verify EInfo returns PubMed database details."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{EUTILS_BASE}/einfo.fcgi",
                params={
                    "db": "pubmed",
                    "retmode": "json",
                },
            )

        assert response.status_code == 200
        data = response.json()

        assert "einforesult" in data
        assert "dbinfo" in data["einforesult"]

        dbinfo = data["einforesult"]["dbinfo"]
        # dbinfo may be a list or dict depending on API version
        if isinstance(dbinfo, list):
            dbinfo = dbinfo[0]
        assert dbinfo["dbname"] == "pubmed"
        assert "count" in dbinfo
        assert "fieldlist" in dbinfo

    @pytest.mark.asyncio
    async def test_multiple_pmid_fetch(self) -> None:
        """Verify fetching multiple PMIDs at once."""
        pmids = [STABLE_PMID, "33408182"]

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{EUTILS_BASE}/esummary.fcgi",
                params={
                    "db": "pubmed",
                    "id": ",".join(pmids),
                    "retmode": "json",
                },
            )

        assert response.status_code == 200
        data = response.json()

        assert "result" in data
        # At least one of the PMIDs should be in results
        result_keys = set(data["result"].keys()) - {"uids"}
        assert len(result_keys) >= 1

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_elink_related_articles(self) -> None:
        """Verify ELink endpoint for related articles."""
        pmid = STABLE_PMID

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{EUTILS_BASE}/elink.fcgi",
                params={
                    "dbfrom": "pubmed",
                    "db": "pubmed",
                    "id": pmid,
                    "cmd": "neighbor",
                    "retmode": "json",
                },
            )

        assert response.status_code == 200
        data = response.json()

        assert "linksets" in data
