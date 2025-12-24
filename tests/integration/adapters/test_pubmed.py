from __future__ import annotations

# tests/integration/adapters/test_pubmed.py
from unittest.mock import MagicMock

import pytest
import respx
from httpx import Response

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.adapters.pubmed.pubmed_client import (
    ENTREZ_API_BASE,
    PubMedAdapter,
)
from bioetl.infrastructure.config import get_settings  # Import get_settings


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger for testing."""
    return MagicMock()


@pytest.fixture
def pubmed_adapter(monkeypatch, mock_logger) -> PubMedAdapter:
    """Fixture to provide a PubMedAdapter instance for testing."""
    monkeypatch.setenv("BIOETL_TEST_MODE", "true")
    get_settings.cache_clear()
    settings = get_settings()  # Load settings

    # Use actual rate from settings if API key is present
    rate = (
        10.0
        if settings.pubmed_api_key and settings.pubmed_api_key.get_secret_value()
        else 3.0
    )

    http_client = UnifiedHTTPClient(
        TokenBucket(rate=rate, capacity=rate * 2),
        CircuitBreaker(provider="pubmed_test"),
    )
    return PubMedAdapter(
        http_client=http_client,
        logger=mock_logger,
        email="test@example.com",  # Use dummy email for tests
        api_key=None,  # Don't use API key for tests to avoid auth issues in replay or strict checks
    )


@pytest.mark.integration
async def test_fetch_publications(pubmed_adapter: PubMedAdapter):
    """
    Tests fetching publications from PubMed.
    Mocked using respx to avoid VCR/Network issues.
    """

    # Mock XML response for efetch
    mock_xml = """<?xml version="1.0"?>
    <PubmedArticleSet>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345</PMID>
                <Article>
                    <ArticleTitle>Test Article 1</ArticleTitle>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>67890</PMID>
                <Article>
                    <ArticleTitle>Test Article 2</ArticleTitle>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
    </PubmedArticleSet>
    """

    # Mock JSON response for esearch
    mock_search_json = {"esearchresult": {"idlist": ["12345", "67890"]}}

    with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
        # Mock search
        respx_mock.get("esearch.fcgi").mock(
            return_value=Response(200, json=mock_search_json)
        )

        # Mock fetch
        respx_mock.get("efetch.fcgi").mock(return_value=Response(200, text=mock_xml))

        async with pubmed_adapter.http_client:
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
@pytest.mark.vcr
async def test_health_check(pubmed_adapter: PubMedAdapter):
    """
    Tests the health check for the PubMed API.
    This test requires a VCR cassette. To record:
    pytest tests/integration/adapters/test_pubmed.py::test_health_check --vcr-record=new_episodes
    """
    async with pubmed_adapter.http_client:
        status = await pubmed_adapter.health_check()
        assert status == HealthStatus.HEALTHY
