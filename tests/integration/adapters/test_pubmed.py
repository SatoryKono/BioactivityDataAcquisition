# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Integration tests for PubMed adapter.

These tests use VCR.py to record/replay HTTP interactions.
To record new cassettes: pytest --vcr-record=new_episodes

Cassettes location: tests/fixtures/vcr/pubmed/
"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.pubmed import ENTREZ_API_BASE, PubMedAdapter
from tests.integration.adapters.pubmed_integration_support import (
    build_pubmed_articles_xml,
    build_pubmed_search_ids,
)

# VCR cassette directory for PubMed adapter tests
# Note: cassette directory is resolved by conftest.py vcr_cassette_dir fixture
# which looks for tests/fixtures/vcr/pubmed/ based on test filename


@pytest.mark.integration
async def test_fetch_publications(pubmed_adapter: PubMedAdapter):
    """
    Tests fetching publications from PubMed.
    Mocked using respx to avoid VCR/Network issues.
    """

    # Mock XML response for efetch
    mock_xml = build_pubmed_articles_xml(
        ("12345", "Test Article 1"),
        ("67890", "Test Article 2"),
    )

    # Mock JSON response for esearch
    mock_search_json = build_pubmed_search_ids("12345", "67890")

    with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
        # Mock search
        respx_mock.get("esearch.fcgi").mock(
            return_value=Response(200, json=mock_search_json)
        )

        # Mock fetch
        respx_mock.get("efetch.fcgi").mock(return_value=Response(200, text=mock_xml))

        records = []
        async for record in pubmed_adapter.fetch(
            "publication", query="crispr", limit=2
        ):
            records.append(record)

        assert len(records) == 2
        assert records[0]["pmid"] == "12345"
        assert records[0]["article_title"] == "Test Article 1"
        assert records[1]["pmid"] == "67890"
        assert records[1]["article_title"] == "Test Article 2"


@pytest.mark.integration
async def test_adapters_pubmed__health_check__d03bddac(pubmed_adapter: PubMedAdapter):
    """Tests the health check for the PubMed API using einfo.fcgi."""
    mock_einfo_json = {
        "header": {"type": "einfo", "version": "0.3"},
        "einforesult": {
            "dbinfo": {
                "dbname": "pubmed",
                "menuname": "PubMed",
                "description": "PubMed bibliographic record",
                "count": "37000000",
            }
        },
    }

    with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
        respx_mock.get("einfo.fcgi").mock(
            return_value=Response(200, json=mock_einfo_json)
        )

        status = await pubmed_adapter.health_check()
        # Under high local load, latency-based probe may report DEGRADED.
        assert status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
