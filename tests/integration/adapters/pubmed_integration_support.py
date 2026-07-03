"""Shared fixtures for PubMed adapter integration tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.pubmed import PubMedAdapter
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs
from tests.integration.adapters.http_integration_support import (
    build_mock_logger,
    managed_http_client,
    reset_http_client_state,
)


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger for PubMed integration tests."""
    return build_mock_logger()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def http_client() -> AsyncIterator[UnifiedHTTPClient]:
    """Provide a shared started HTTP client for PubMed integration tests."""
    async with managed_http_client(
        provider="pubmed",
        rate=10.0,
        capacity=20.0,
        limiter_provider="pubmed_test",
        circuit_breaker_provider="pubmed_test",
    ) as client:
        yield client


@pytest.fixture
def pubmed_adapter(
    http_client: UnifiedHTTPClient,
    mock_logger: MagicMock,
) -> PubMedAdapter:
    """Create a PubMed adapter with canonical integration-test defaults."""
    reset_http_client_state(http_client)
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


def build_pubmed_search_ids(*pmids: str) -> dict[str, dict[str, list[str]]]:
    """Build the minimal PubMed search response payload for a PMIDs list."""
    return {"esearchresult": {"idlist": list(pmids)}}


def build_pubmed_articles_xml(*articles: tuple[str, str]) -> str:
    """Build a minimal ``PubmedArticleSet`` XML payload from ``(pmid, title)`` pairs."""
    article_nodes = "\n".join(
        f"""        <PubmedArticle>
            <MedlineCitation>
                <PMID>{pmid}</PMID>
                <Article>
                    <ArticleTitle>{title}</ArticleTitle>
                </Article>
            </MedlineCitation>
        </PubmedArticle>"""
        for pmid, title in articles
    )
    return f"""<?xml version="1.0"?>
    <PubmedArticleSet>
{article_nodes}
    </PubmedArticleSet>
    """
