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
"""Integration checks for HTTP retry semantics on real adapter paths."""

from __future__ import annotations

from unittest.mock import MagicMock

from httpx import Request, Response
import pytest
import respx

from bioetl.composition.factories.datasource.crossref import create_crossref_adapter
from bioetl.infrastructure.adapters.crossref.client import CROSSREF_API_BASE
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.pubmed import ENTREZ_API_BASE, PubMedAdapter
from bioetl.domain.resilience import RetryConfig
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs


def _build_retrying_http_client(provider: str) -> UnifiedHTTPClient:
    """Build a real UnifiedHTTPClient with deterministic retry behavior."""
    return UnifiedHTTPClient(
        rate_limiter=TokenBucketRateLimiter(
            rate=50.0,
            capacity=50.0,
            provider=provider,
        ),
        circuit_breaker=CircuitBreakerGuard(provider=provider),
        retry_config=RetryConfig(
            max_attempts=2,
            base_delay=0.0,
            max_delay=0.0,
            jitter_range=(0.0, 0.0),
        ),
        timeout=10.0,
        provider=provider,
    )


@pytest.fixture
def mock_logger() -> MagicMock:
    logger = MagicMock()
    logger.bind.return_value = logger
    return logger


@pytest.mark.integration
async def test_crossref_adapter_retries_retryable_http_status(
    mock_logger: MagicMock,
) -> None:
    """CrossRef adapter should recover from a transient 503 via UnifiedHTTPClient retry."""
    adapter = create_crossref_adapter(
        http_client=_build_retrying_http_client("crossref_retry_semantics"),
        logger=mock_logger,
        settings=None,
        mailto="bioetl-test@example.com",
        batch_size=10,
    )
    call_count = 0

    def _crossref_side_effect(request: Request) -> Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return Response(
                503,
                request=request,
                json={"status": "error", "message": {"items": []}},
            )
        return Response(
            200,
            request=request,
            json={
                "status": "ok",
                "message": {
                    "items": [
                        {
                            "DOI": "10.1038/nature12373",
                            "title": ["Crystal structure of rhodopsin"],
                        }
                    ]
                },
            },
        )

    with respx.mock(base_url=CROSSREF_API_BASE) as respx_mock:
        route = respx_mock.get("/works")
        route.side_effect = _crossref_side_effect
        async with adapter._http_client:
            records = [
                record
                async for record in adapter.fetch_filtered(
                    entity_type="publication",
                    filter_ids=["10.1038/nature12373"],
                    filter_field="doi",
                )
            ]

    assert route.call_count == 2
    assert len(records) == 1
    assert records[0]["DOI"] == "10.1038/nature12373"


@pytest.mark.integration
async def test_pubmed_adapter_retries_rate_limit_response(
    mock_logger: MagicMock,
) -> None:
    """PubMed adapter should retry once on a transient 429 and then succeed."""
    adapter = PubMedAdapter(
        http_client=_build_retrying_http_client("pubmed_retry_semantics"),
        logger=mock_logger,
        email="bioetl-test@example.com",
        api_key=None,
        batch_size=100,
        **build_http_adapter_runtime_kwargs(
            "pubmed",
            logger=mock_logger,
            include_fallback_service=True,
        ),
    )
    call_count = 0
    mock_xml = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>35486828</PMID>
      <Article><ArticleTitle>Retry Success</ArticleTitle></Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""

    def _pubmed_side_effect(request: Request) -> Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return Response(
                429,
                request=request,
                headers={"Retry-After": "0"},
                text="rate limited",
            )
        return Response(200, request=request, text=mock_xml)

    with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
        route = respx_mock.get("efetch.fcgi")
        route.side_effect = _pubmed_side_effect
        async with adapter._http_client:
            records = [
                record
                async for record in adapter.fetch_filtered(
                    entity_type="publication",
                    filter_ids=["35486828"],
                    filter_field="pmid",
                )
            ]

    assert route.call_count == 2
    assert len(records) == 1
    assert records[0]["pmid"] == "35486828"
