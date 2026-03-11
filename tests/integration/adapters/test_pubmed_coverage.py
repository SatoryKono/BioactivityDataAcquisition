"""Additional tests for PubMed adapter to improve coverage."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import respx
from httpx import Response
from pydantic import SecretStr

from bioetl.domain.entities.pubmed import ArticleRecord
from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.pubmed.client import (
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
        TokenBucketRateLimiter(rate=10.0, capacity=20.0),
        CircuitBreakerGuard(provider="pubmed_test"),
        retry_config=RetryConfig(max_attempts=1, base_delay=0.0),
        timeout=0.5,
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

        async with pubmed_adapter._http_client:
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
        # Primary fetch (pmid 12345 and missing_id)
        # fetch_filtered will be called with ["12345", "missing_id"]
        # which results in id=12345,missing_id
        respx_mock.get(
            "efetch.fcgi",
            params={
                "id": "12345,missing_id",
                "db": "pubmed",
                "retmode": "xml",
                "rettype": "abstract",
                "email": "test@example.com",
            },
        ).mock(return_value=Response(200, text=mock_xml))
        # Fallback search by title
        respx_mock.get("esearch.fcgi").mock(
            return_value=Response(200, json=mock_search_json)
        )
        # Fallback fetch (pmid 67890)
        respx_mock.get(
            "efetch.fcgi",
            params={
                "id": "67890",
                "db": "pubmed",
                "retmode": "xml",
                "rettype": "abstract",
                "email": "test@example.com",
            },
        ).mock(return_value=Response(200, text=mock_fallback_xml))

        async with pubmed_adapter._http_client:
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

        async with pubmed_adapter._http_client:
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

    pubmed_adapter._http_client = MagicMock(spec=UnifiedHTTPClient)
    # Mock __aexit__ which is called by await http_client.__aexit__
    pubmed_adapter._http_client.__aexit__ = AsyncMock()

    await pubmed_adapter.aclose()
    assert pubmed_adapter._http_client.__aexit__.called


@pytest.mark.integration
async def test_fetch_batch_xml_parse_error(pubmed_adapter: PubMedAdapter, mock_logger):
    # Mocking efetch with invalid XML
    with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
        respx_mock.get("efetch.fcgi").mock(
            return_value=Response(200, text="invalid xml")
        )

        async with pubmed_adapter._http_client:
            # We need to access the private method to test this specific branch
            records = await pubmed_adapter._fetch_batch(["12345"])
            assert records == []
            assert mock_logger.error.called


@pytest.mark.integration
async def test_fetch_batch_network_error(pubmed_adapter: PubMedAdapter):
    with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
        respx_mock.get("efetch.fcgi").mock(return_value=Response(500))

        async with pubmed_adapter._http_client:
            with pytest.raises(Exception):
                await pubmed_adapter._fetch_batch(["12345"])


@pytest.mark.integration
async def test_get_pmids_error(pubmed_adapter: PubMedAdapter):
    with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
        respx_mock.get("esearch.fcgi").mock(return_value=Response(500))

        async with pubmed_adapter._http_client:
            with pytest.raises(Exception):
                await pubmed_adapter._get_pmids("query", 10)


@pytest.mark.integration
async def test_search_by_title_error(pubmed_adapter: PubMedAdapter, mock_logger):
    # This should trigger the exception block in _search_by_title
    # which returns [] and logs debug
    with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
        respx_mock.get("esearch.fcgi").mock(side_effect=RuntimeError("search error"))

        async with pubmed_adapter._http_client:
            results = await pubmed_adapter._search_by_title("some title")
            assert results == []
            assert mock_logger.debug.called


@pytest.mark.integration
async def test_probe_health_explicit(pubmed_adapter: PubMedAdapter):
    mock_health_json = {
        "header": {"type": "einfo", "version": "0.3"},
        "einforesult": {
            "dbinfo": {
                "dbname": "pubmed",
                "menuname": "PubMed",
                "description": "PubMed bibliographic record",
                "dbbuild": "Build250214-2337m.1",
                "count": "37000000",
                "lastupdate": "2025/02/15 06:07",
            }
        },
    }
    with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
        respx_mock.get("einfo.fcgi").mock(
            return_value=Response(200, json=mock_health_json)
        )

        async with pubmed_adapter._http_client:
            status = await pubmed_adapter._probe_health()
            assert status == HealthStatus.HEALTHY


@pytest.mark.integration
async def test_probe_health_degraded(pubmed_adapter: PubMedAdapter):
    mock_health_json = {
        "header": {"type": "einfo", "version": "0.3"},
        "einforesult": {
            "dbinfo": {
                "dbname": "pubmed",
                "menuname": "PubMed",
                "description": "PubMed bibliographic record",
                "dbbuild": "Build250214-2337m.1",
                "count": "37000000",
                "lastupdate": "2025/02/15 06:07",
            }
        },
    }

    # Simulate slow response by advancing time.monotonic() by 5.1s
    # instead of actually sleeping, to keep the test fast.
    import time
    from unittest.mock import patch

    call_count = 0
    real_monotonic = time.monotonic

    def fake_monotonic() -> float:
        nonlocal call_count
        call_count += 1
        base = real_monotonic()
        # After the first call (start_time), advance by 5.1s
        if call_count >= 2:
            return base + 5.1
        return base

    with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
        respx_mock.get("einfo.fcgi").mock(
            return_value=Response(200, json=mock_health_json)
        )

        with patch(
            "bioetl.infrastructure.adapters.pubmed._health.time.monotonic",
            side_effect=fake_monotonic,
        ):
            async with pubmed_adapter._http_client:
                status = await pubmed_adapter._probe_health()
                assert status == HealthStatus.DEGRADED


@pytest.mark.integration
async def test_probe_health_unhealthy(pubmed_adapter: PubMedAdapter):
    with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
        respx_mock.get("einfo.fcgi").mock(return_value=Response(500))

        async with pubmed_adapter._http_client:
            # health_check calls _probe_health and catches exceptions
            status = await pubmed_adapter.health_check()
            assert status == HealthStatus.UNHEALTHY
