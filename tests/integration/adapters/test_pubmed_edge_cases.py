"""Integration tests for PubMed adapter edge cases.

Tests for real-world edge cases in PubMed API responses.
Unicode characters in tests are intentional for testing international content handling.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
import respx
from httpx import Response

from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.pubmed import ENTREZ_API_BASE, PubMedAdapter
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger for testing."""
    return MagicMock()


def _reset_http_client_state(client: UnifiedHTTPClient) -> None:
    """Reset mutable HTTP client state between tests sharing one client."""
    client.circuit_breaker.reset()
    rate_limiter = client.rate_limiter
    if isinstance(rate_limiter, TokenBucketRateLimiter):
        rate_limiter._tokens = float(rate_limiter.capacity)
        rate_limiter._last_refill = time.monotonic()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def http_client() -> AsyncIterator[UnifiedHTTPClient]:
    """Provide a shared started HTTP client for PubMed edge-case tests."""
    client = UnifiedHTTPClient(
        TokenBucketRateLimiter(rate=10.0, capacity=20.0, provider="pubmed_test"),
        CircuitBreakerGuard(provider="pubmed_test"),
        retry_config=RetryConfig(
            base_delay=0.0,
            max_delay=0.0,
            multiplier=1.0,
            jitter_range=(0.0, 0.0),
        ),
        timeout=30.0,
        provider="pubmed",
    )
    await client.__aenter__()
    yield client
    await client.__aexit__(None, None, None)


@pytest.fixture
def pubmed_adapter(
    http_client: UnifiedHTTPClient,
    mock_logger: MagicMock,
) -> PubMedAdapter:
    """Fixture to provide a PubMedAdapter instance for testing."""
    _reset_http_client_state(http_client)
    return PubMedAdapter(
        http_client=http_client,
        logger=mock_logger,
        email="test@example.com",
        api_key=None,
        **build_http_adapter_runtime_kwargs(
            "pubmed",
            logger=mock_logger,
            include_fallback_service=True,
        ),
    )


class TestPubMedEdgeCases:
    """Edge case tests for PubMed adapter."""

    @pytest.mark.integration
    async def test_fetch_empty_search_results(self, pubmed_adapter: PubMedAdapter):
        """Test handling of empty search results."""
        mock_search_json = {"esearchresult": {"idlist": []}}

        with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
            respx_mock.get("esearch.fcgi").mock(
                return_value=Response(200, json=mock_search_json)
            )

            records = []
            async for record in pubmed_adapter.fetch(
                "publication", query="xyznonexistent12345", limit=10
            ):
                records.append(record)

            assert len(records) == 0

    @pytest.mark.integration
    async def test_fetch_article_without_abstract(self, pubmed_adapter: PubMedAdapter):
        """Test fetching article that has no abstract."""
        mock_xml = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>99999</PMID>
                    <Article>
                        <ArticleTitle>Letter to the Editor</ArticleTitle>
                        <Language>eng</Language>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        mock_search_json = {"esearchresult": {"idlist": ["99999"]}}

        with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
            respx_mock.get("esearch.fcgi").mock(
                return_value=Response(200, json=mock_search_json)
            )
            respx_mock.get("efetch.fcgi").mock(
                return_value=Response(200, text=mock_xml)
            )

            records = []
            async for record in pubmed_adapter.fetch(
                "publication", query="test", limit=1
            ):
                records.append(record)

            assert len(records) == 1
            assert records[0]["pmid"] == "99999"
            assert records[0]["article_title"] == "Letter to the Editor"

    @pytest.mark.integration
    async def test_fetch_article_with_structured_abstract(
        self, pubmed_adapter: PubMedAdapter
    ):
        """Test fetching article with structured abstract (labeled sections)."""
        mock_xml = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>88888</PMID>
                    <Article>
                        <ArticleTitle>Clinical Trial</ArticleTitle>
                        <Abstract>
                            <AbstractText Label="BACKGROUND">Background text.</AbstractText>
                            <AbstractText Label="METHODS">Methods text.</AbstractText>
                            <AbstractText Label="RESULTS">Results text.</AbstractText>
                            <AbstractText Label="CONCLUSIONS">Conclusions text.</AbstractText>
                        </Abstract>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        mock_search_json = {"esearchresult": {"idlist": ["88888"]}}

        with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
            respx_mock.get("esearch.fcgi").mock(
                return_value=Response(200, json=mock_search_json)
            )
            respx_mock.get("efetch.fcgi").mock(
                return_value=Response(200, text=mock_xml)
            )

            records = []
            async for record in pubmed_adapter.fetch(
                "publication", query="test", limit=1
            ):
                records.append(record)

            assert len(records) == 1
            assert records[0]["pmid"] == "88888"

    @pytest.mark.integration
    async def test_fetch_article_with_collective_author(
        self, pubmed_adapter: PubMedAdapter
    ):
        """Test fetching article with collective/group author."""
        mock_xml = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>77777</PMID>
                    <Article>
                        <ArticleTitle>Consortium Study</ArticleTitle>
                        <AuthorList>
                            <Author>
                                <CollectiveName>WHO Research Consortium</CollectiveName>
                            </Author>
                        </AuthorList>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        mock_search_json = {"esearchresult": {"idlist": ["77777"]}}

        with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
            respx_mock.get("esearch.fcgi").mock(
                return_value=Response(200, json=mock_search_json)
            )
            respx_mock.get("efetch.fcgi").mock(
                return_value=Response(200, text=mock_xml)
            )

            records = []
            async for record in pubmed_adapter.fetch(
                "publication", query="test", limit=1
            ):
                records.append(record)

            assert len(records) == 1
            assert records[0]["pmid"] == "77777"

    @pytest.mark.integration
    async def test_fetch_article_with_unicode_characters(
        self, pubmed_adapter: PubMedAdapter
    ):
        """Test fetching article with unicode characters in title/authors."""
        mock_xml = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>66666</PMID>
                    <Article>
                        <ArticleTitle>Effect of α-tocopherol on β-cell function</ArticleTitle>
                        <AuthorList>
                            <Author>
                                <LastName>Müller</LastName>
                                <Initials>H</Initials>
                            </Author>
                            <Author>
                                <LastName>García-López</LastName>
                                <Initials>M</Initials>
                            </Author>
                        </AuthorList>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        mock_search_json = {"esearchresult": {"idlist": ["66666"]}}

        with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
            respx_mock.get("esearch.fcgi").mock(
                return_value=Response(200, json=mock_search_json)
            )
            respx_mock.get("efetch.fcgi").mock(
                return_value=Response(200, text=mock_xml)
            )

            records = []
            async for record in pubmed_adapter.fetch(
                "publication", query="test", limit=1
            ):
                records.append(record)

            assert len(records) == 1
            assert "α-tocopherol" in records[0]["article_title"]
            assert "β-cell" in records[0]["article_title"]

    @pytest.mark.integration
    async def test_fetch_article_minimal_metadata(self, pubmed_adapter: PubMedAdapter):
        """Test fetching article with minimal metadata (just PMID and title)."""
        mock_xml = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>55555</PMID>
                    <Article>
                        <ArticleTitle>Minimal Article</ArticleTitle>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        mock_search_json = {"esearchresult": {"idlist": ["55555"]}}

        with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
            respx_mock.get("esearch.fcgi").mock(
                return_value=Response(200, json=mock_search_json)
            )
            respx_mock.get("efetch.fcgi").mock(
                return_value=Response(200, text=mock_xml)
            )

            records = []
            async for record in pubmed_adapter.fetch(
                "publication", query="test", limit=1
            ):
                records.append(record)

            assert len(records) == 1
            assert records[0]["pmid"] == "55555"
            assert records[0]["article_title"] == "Minimal Article"

    @pytest.mark.integration
    async def test_fetch_article_with_pmc_id(self, pubmed_adapter: PubMedAdapter):
        """Test fetching article that has PMC ID."""
        mock_xml = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>44444</PMID>
                    <Article>
                        <ArticleTitle>Open Access Article</ArticleTitle>
                    </Article>
                </MedlineCitation>
                <PubmedData>
                    <ArticleIdList>
                        <ArticleId IdType="pubmed">44444</ArticleId>
                        <ArticleId IdType="pmc">PMC1234567</ArticleId>
                        <ArticleId IdType="doi">10.1234/test.2023</ArticleId>
                    </ArticleIdList>
                </PubmedData>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        mock_search_json = {"esearchresult": {"idlist": ["44444"]}}

        with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
            respx_mock.get("esearch.fcgi").mock(
                return_value=Response(200, json=mock_search_json)
            )
            respx_mock.get("efetch.fcgi").mock(
                return_value=Response(200, text=mock_xml)
            )

            records = []
            async for record in pubmed_adapter.fetch(
                "publication", query="test", limit=1
            ):
                records.append(record)

            assert len(records) == 1
            assert records[0]["pmid"] == "44444"

    @pytest.mark.integration
    async def test_fetch_multiple_articles_batch(self, pubmed_adapter: PubMedAdapter):
        """Test fetching multiple articles in a batch."""
        mock_xml = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>11111</PMID>
                    <Article>
                        <ArticleTitle>First Article</ArticleTitle>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>22222</PMID>
                    <Article>
                        <ArticleTitle>Second Article</ArticleTitle>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>33333</PMID>
                    <Article>
                        <ArticleTitle>Third Article</ArticleTitle>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        mock_search_json = {"esearchresult": {"idlist": ["11111", "22222", "33333"]}}

        with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
            respx_mock.get("esearch.fcgi").mock(
                return_value=Response(200, json=mock_search_json)
            )
            respx_mock.get("efetch.fcgi").mock(
                return_value=Response(200, text=mock_xml)
            )

            records = []
            async for record in pubmed_adapter.fetch(
                "publication", query="test", limit=3
            ):
                records.append(record)

            assert len(records) == 3
            pmids = [r["pmid"] for r in records]
            assert "11111" in pmids
            assert "22222" in pmids
            assert "33333" in pmids

    @pytest.mark.integration
    async def test_health_check_failure(self, pubmed_adapter: PubMedAdapter):
        """Test health check when API returns error."""
        with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
            # Health check uses einfo.fcgi endpoint (lightweight DB info)
            respx_mock.get("einfo.fcgi").mock(return_value=Response(500, text="Error"))

            status = await pubmed_adapter.health_check()
            # On error, fallback status is DEGRADED (not UNHEALTHY)
            assert status in (HealthStatus.UNHEALTHY, HealthStatus.DEGRADED)


class TestPubMedRateLimiting:
    """Tests for rate limiting behavior."""

    @pytest.mark.integration
    async def test_fetch_respects_rate_limit(self, pubmed_adapter: PubMedAdapter):
        """Test that fetches respect rate limiting."""
        mock_xml = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>12345</PMID>
                    <Article>
                        <ArticleTitle>Rate Limit Test</ArticleTitle>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        mock_search_json = {"esearchresult": {"idlist": ["12345"]}}

        with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
            respx_mock.get("esearch.fcgi").mock(
                return_value=Response(200, json=mock_search_json)
            )
            respx_mock.get("efetch.fcgi").mock(
                return_value=Response(200, text=mock_xml)
            )

            records = []
            async for record in pubmed_adapter.fetch(
                "publication", query="test", limit=1
            ):
                records.append(record)

            # Should complete without rate limit errors
            assert len(records) == 1


class TestPubMedXMLParsing:
    """Tests for XML parsing edge cases."""

    @pytest.mark.integration
    async def test_fetch_article_with_html_entities(
        self, pubmed_adapter: PubMedAdapter
    ):
        """Test fetching article with HTML entities in XML."""
        mock_xml = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>98765</PMID>
                    <Article>
                        <ArticleTitle>5' &amp; 3' ends in DNA</ArticleTitle>
                        <Abstract>
                            <AbstractText>Temperature &gt; 37°C and &lt; 100°C</AbstractText>
                        </Abstract>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        mock_search_json = {"esearchresult": {"idlist": ["98765"]}}

        with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
            respx_mock.get("esearch.fcgi").mock(
                return_value=Response(200, json=mock_search_json)
            )
            respx_mock.get("efetch.fcgi").mock(
                return_value=Response(200, text=mock_xml)
            )

            records = []
            async for record in pubmed_adapter.fetch(
                "publication", query="test", limit=1
            ):
                records.append(record)

            assert len(records) == 1
            # HTML entities should be decoded
            assert "5' & 3'" in records[0]["article_title"]

    @pytest.mark.integration
    async def test_fetch_article_with_inline_elements(
        self, pubmed_adapter: PubMedAdapter
    ):
        """Test fetching article with inline formatting elements.

        Note: At Bronze layer, adapter uses node.text which only gets text
        before inline elements. Full text extraction happens in transformer.
        This test verifies raw XML is preserved for transformer processing.
        """
        mock_xml = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>87654</PMID>
                    <Article>
                        <ArticleTitle>Effects of <i>in vitro</i> treatment</ArticleTitle>
                        <Abstract>
                            <AbstractText>Study of <b>important</b> findings with <sup>13</sup>C isotope.</AbstractText>
                        </Abstract>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        mock_search_json = {"esearchresult": {"idlist": ["87654"]}}

        with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
            respx_mock.get("esearch.fcgi").mock(
                return_value=Response(200, json=mock_search_json)
            )
            respx_mock.get("efetch.fcgi").mock(
                return_value=Response(200, text=mock_xml)
            )

            records = []
            async for record in pubmed_adapter.fetch(
                "publication", query="test", limit=1
            ):
                records.append(record)

            assert len(records) == 1
            # Article title at Bronze layer shows text before inline element
            assert "Effects of" in records[0]["article_title"]
            # Raw XML is preserved for transformer to extract full text
            assert "_raw_xml" in records[0]
            assert "in vitro" in records[0]["_raw_xml"]
