"""Additional tests for PubMed adapter to improve coverage."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import respx
from httpx import Response
from pydantic import SecretStr

from bioetl.domain.entities.pubmed import ArticleRecord
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.adapters.pubmed.pubmed_client import (
    ENTREZ_API_BASE,
    PubMedAdapter,
    _create_pubmed_adapter,
)


@pytest.fixture
def mock_logger() -> MagicMock:
    return MagicMock()


@pytest.fixture
def pubmed_adapter(mock_logger) -> PubMedAdapter:
    http_client = UnifiedHTTPClient(
        TokenBucket(rate=10.0, capacity=20.0),
        CircuitBreaker(provider="pubmed_test"),
    )
    return PubMedAdapter(
        http_client=http_client,
        logger=mock_logger,
        email="test@example.com",
    )


@pytest.mark.integration
async def test_fetch_filtered(pubmed_adapter: PubMedAdapter):
    mock_xml = """<?xml version="1.0"?>
    <PubmedArticleSet>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345</PMID>
                <Article><ArticleTitle>Test 1</ArticleTitle></Article>
            </MedlineCitation>
        </PubmedArticle>
    </PubmedArticleSet>
    """
    with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
        respx_mock.get("efetch.fcgi").mock(return_value=Response(200, text=mock_xml))

        async with pubmed_adapter.http_client:
            records = []
            async for record in pubmed_adapter.fetch_filtered(
                "publication", ["12345"], "pmid"
            ):
                records.append(record)

            assert len(records) == 1
            assert records[0]["pmid"] == "12345"
            assert records[0]["_lookup_method"] == "pmid"

    # Test error category for invalid entity type
    with pytest.raises(ValueError, match="PubMedAdapter only supports 'publication'"):
        async for _ in pubmed_adapter.fetch_filtered("invalid", ["12345"], "pmid"):
            pass


@pytest.mark.integration
async def test_fetch_filtered_with_fallback(pubmed_adapter: PubMedAdapter):
    mock_xml = """<?xml version="1.0"?>
    <PubmedArticleSet>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345</PMID>
                <Article><ArticleTitle>Test 1</ArticleTitle></Article>
            </MedlineCitation>
        </PubmedArticle>
    </PubmedArticleSet>
    """
    # For fallback search
    mock_search_json = {"esearchresult": {"idlist": ["67890"]}}
    mock_fallback_xml = """<?xml version="1.0"?>
    <PubmedArticleSet>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>67890</PMID>
                <Article><ArticleTitle>Fallback Article</ArticleTitle></Article>
            </MedlineCitation>
        </PubmedArticle>
    </PubmedArticleSet>
    """

    with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
        # Primary fetch (pmid 12345)
        # Use simple params matching
        respx_mock.get("efetch.fcgi", params={"id": "12345", "db": "pubmed", "retmode": "xml", "rettype": "abstract", "email": "test@example.com"}).mock(
            return_value=Response(200, text=mock_xml)
        )
        # Fallback search by title
        respx_mock.get("esearch.fcgi").mock(
            return_value=Response(200, json=mock_search_json)
        )
        # Fallback fetch (pmid 67890)
        respx_mock.get("efetch.fcgi", params={"id": "67890", "db": "pubmed", "retmode": "xml", "rettype": "abstract", "email": "test@example.com"}).mock(
            return_value=Response(200, text=mock_fallback_xml)
        )

        async with pubmed_adapter.http_client:
            records = []
            fallback_mapping = {"missing_id": "Fallback Title"}
            async for record in pubmed_adapter.fetch_filtered_with_fallback(
                entity_type="publication",
                filter_ids=["12345", "missing_id"],
                filter_field="pmid",
                fallback_mapping=fallback_mapping,
            ):
                records.append(record)

            assert len(records) >= 1
            # Check if we got the fallback record too
            pmids = [r["pmid"] for r in records]
            assert "12345" in pmids
            assert "67890" in pmids


@pytest.mark.integration
async def test_fetch_as_models(pubmed_adapter: PubMedAdapter):
    mock_xml = """<?xml version="1.0"?>
    <PubmedArticleSet>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345</PMID>
                <Article><ArticleTitle>Test Model</ArticleTitle></Article>
            </MedlineCitation>
        </PubmedArticle>
    </PubmedArticleSet>
    """
    mock_search_json = {"esearchresult": {"idlist": ["12345"]}}

    with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
        respx_mock.get("esearch.fcgi").mock(
            return_value=Response(200, json=mock_search_json)
        )
        respx_mock.get("efetch.fcgi").mock(return_value=Response(200, text=mock_xml))

        async with pubmed_adapter.http_client:
            models = []
            async for model in pubmed_adapter.fetch_as_models(
                "publication", query="test", limit=1
            ):
                models.append(model)

            assert len(models) == 1
            assert isinstance(models[0], ArticleRecord)
            assert models[0].pmid == "12345"
            assert models[0].title == "Test Model"


@pytest.mark.integration
async def test_adapter_factory(mock_logger):
    settings = MagicMock()
    settings.default_email = "factory@example.com"
    settings.pubmed_api_key = SecretStr("test_key")

    http_client = MagicMock(spec=UnifiedHTTPClient)

    adapter = _create_pubmed_adapter(
        http_client=http_client,
        logger=mock_logger,
        settings=settings,
        batch_size=100,
    )

    assert adapter.email == "factory@example.com"
    assert adapter.api_key == "test_key"
    assert adapter.batch_size == 100


@pytest.mark.integration
async def test_adapter_factory_missing_args():
    with pytest.raises(ValueError, match="PubMed adapter requires email"):
        _create_pubmed_adapter(None, None, None)

    with pytest.raises(ValueError, match="PubMed adapter requires http_client"):
        _create_pubmed_adapter(None, MagicMock(), MagicMock(default_email="a@b.com"))


@pytest.mark.integration
async def test_adapter_aclose(pubmed_adapter: PubMedAdapter):
    from unittest.mock import AsyncMock
    pubmed_adapter.http_client = MagicMock(spec=UnifiedHTTPClient)
    # Mock __aexit__ which is called by await http_client.__aexit__
    pubmed_adapter.http_client.__aexit__ = AsyncMock()

    await pubmed_adapter.aclose()
    assert pubmed_adapter.http_client.__aexit__.called
