"""Integration tests for external ID verification via real provider adapters.

These tests verify adapter-backed lookup behavior (found/not-found/fallback)
using real adapter code paths and HTTP mocking via respx.
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock

from httpx import Response
import pytest
import respx

from bioetl.composition.factories.datasource.crossref import create_crossref_adapter
from bioetl.infrastructure.adapters.chembl import ChemblAdapter
from bioetl.infrastructure.adapters.chembl.constants import CHEMBL_API_BASE
from bioetl.infrastructure.adapters.crossref.client import (
    CROSSREF_API_BASE,
)
from bioetl.infrastructure.adapters.crossref import CrossRefAdapter
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.openalex.client import (
    OPENALEX_API_BASE,
)
from bioetl.infrastructure.adapters.openalex import OpenAlexAdapter
from bioetl.infrastructure.adapters.pubmed import ENTREZ_API_BASE, PubMedAdapter
from bioetl.infrastructure.adapters.semanticscholar import SemanticScholarAdapter
from bioetl.infrastructure.adapters.semanticscholar.constants import (
    SEMANTICSCHOLAR_BASE_URL,
)
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs


def _build_http_client(provider: str) -> UnifiedHTTPClient:
    return UnifiedHTTPClient(
        rate_limiter=TokenBucketRateLimiter(
            rate=10.0, capacity=20.0, provider=provider
        ),
        circuit_breaker=CircuitBreakerGuard(provider=provider),
        timeout=15.0,
    )


@pytest.fixture
def mock_logger() -> MagicMock:
    logger = MagicMock()
    logger.bind.return_value = logger
    return logger


@pytest.fixture
def crossref_adapter(mock_logger: MagicMock) -> CrossRefAdapter:
    return create_crossref_adapter(
        http_client=_build_http_client("crossref_external_verification"),
        logger=mock_logger,
        settings=None,
        mailto="bioetl-test@example.com",
        batch_size=10,
    )


@pytest.fixture
def pubmed_adapter(mock_logger: MagicMock) -> PubMedAdapter:
    return PubMedAdapter(
        http_client=_build_http_client("pubmed_external_verification"),
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


@pytest.fixture
def openalex_adapter(mock_logger: MagicMock) -> OpenAlexAdapter:
    return OpenAlexAdapter(
        http_client=_build_http_client("openalex_external_verification"),
        logger=mock_logger,
        mailto="bioetl-test@example.com",
        batch_size=10,
        **build_http_adapter_runtime_kwargs(
            "openalex",
            logger=mock_logger,
            include_fallback_service=True,
        ),
    )


@pytest.fixture
def semanticscholar_adapter(mock_logger: MagicMock) -> SemanticScholarAdapter:
    return SemanticScholarAdapter(
        http_client=_build_http_client("semanticscholar_external_verification"),
        logger=mock_logger,
        batch_size=10,
        **build_http_adapter_runtime_kwargs(
            "semanticscholar",
            logger=mock_logger,
            include_fallback_service=True,
        ),
    )


@pytest.fixture
def chembl_adapter(mock_logger: MagicMock) -> ChemblAdapter:
    return ChemblAdapter(
        http_client=_build_http_client("chembl_external_verification"),
        logger=mock_logger,
    )


@pytest.mark.integration
class TestCrossRefExternalVerification:
    async def test_doi_found(self, crossref_adapter: CrossRefAdapter) -> None:
        response_json = {
            "status": "ok",
            "message": {
                "items": [
                    {
                        "DOI": "10.1038/nature12373",
                        "title": ["Crystal structure of rhodopsin"],
                    }
                ]
            },
        }
        with respx.mock(base_url=CROSSREF_API_BASE) as respx_mock:
            respx_mock.get("/works").mock(
                return_value=Response(200, json=response_json)
            )
            async with crossref_adapter._http_client:
                records = [
                    record
                    async for record in crossref_adapter.fetch_filtered(
                        entity_type="publication",
                        filter_ids=["10.1038/nature12373"],
                        filter_field="doi",
                    )
                ]

        assert len(records) == 1
        assert records[0]["DOI"] == "10.1038/nature12373"
        assert records[0]["_lookup_method"] == "doi"

    async def test_doi_not_found(self, crossref_adapter: CrossRefAdapter) -> None:
        with respx.mock(base_url=CROSSREF_API_BASE) as respx_mock:
            respx_mock.get("/works").mock(
                return_value=Response(
                    200,
                    json={"status": "ok", "message": {"items": []}},
                )
            )
            async with crossref_adapter._http_client:
                records = [
                    record
                    async for record in crossref_adapter.fetch_filtered(
                        entity_type="publication",
                        filter_ids=["10.9999/nonexistent.000"],
                        filter_field="doi",
                    )
                ]

        assert records == []

    async def test_invalid_entity_type_raises(
        self, crossref_adapter: CrossRefAdapter
    ) -> None:
        async with crossref_adapter._http_client:
            with pytest.raises(
                ValueError, match="CrossRefAdapter supports 'work' or 'publication'"
            ):
                async for _ in crossref_adapter.fetch_filtered(
                    entity_type="invalid_entity",
                    filter_ids=["10.1038/nature12373"],
                    filter_field="doi",
                ):
                    continue

    async def test_unsupported_filter_field_logs_warning(
        self,
        crossref_adapter: CrossRefAdapter,
        mock_logger: MagicMock,
    ) -> None:
        response_json = {
            "status": "ok",
            "message": {
                "items": [
                    {
                        "DOI": "10.1038/nature12373",
                        "title": ["Crystal structure of rhodopsin"],
                    }
                ]
            },
        }
        with respx.mock(base_url=CROSSREF_API_BASE) as respx_mock:
            respx_mock.get("/works").mock(
                return_value=Response(200, json=response_json)
            )
            async with crossref_adapter._http_client:
                records = [
                    record
                    async for record in crossref_adapter.fetch_filtered(
                        entity_type="publication",
                        filter_ids=["10.1038/nature12373"],
                        filter_field="title",
                    )
                ]

        assert len(records) == 1
        assert records[0]["_lookup_method"] == "doi"
        assert any(
            call.args
            and call.args[0] == "unsupported_filter_field"
            and call.kwargs.get("field") == "title"
            for call in mock_logger.warning.call_args_list
        )


@pytest.mark.integration
class TestPubMedExternalVerification:
    async def test_pmid_found(self, pubmed_adapter: PubMedAdapter) -> None:
        mock_xml = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>35486828</PMID>
      <Article><ArticleTitle>Test Article</ArticleTitle></Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""
        with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
            respx_mock.get("efetch.fcgi").mock(
                return_value=Response(200, text=mock_xml)
            )
            async with pubmed_adapter._http_client:
                records = [
                    record
                    async for record in pubmed_adapter.fetch_filtered(
                        entity_type="publication",
                        filter_ids=["35486828"],
                        filter_field="pmid",
                    )
                ]

        assert len(records) == 1
        assert records[0]["pmid"] == "35486828"
        assert records[0]["_lookup_method"] == "pmid"

    async def test_invalid_entity_type_raises(
        self, pubmed_adapter: PubMedAdapter
    ) -> None:
        async with pubmed_adapter._http_client:
            with pytest.raises(ValueError, match="only supports 'publication'"):
                async for _ in pubmed_adapter.fetch_filtered(
                    entity_type="invalid_entity",
                    filter_ids=["35486828"],
                    filter_field="pmid",
                ):
                    continue


@pytest.mark.integration
class TestOpenAlexExternalVerification:
    async def test_doi_found(self, openalex_adapter: OpenAlexAdapter) -> None:
        response_json = {
            "results": [
                {
                    "id": "https://openalex.org/W2148763428",
                    "doi": "https://doi.org/10.1038/nature12373",
                    "title": "Crystal structure of rhodopsin",
                }
            ],
            "meta": {"count": 1},
        }
        with respx.mock(base_url=OPENALEX_API_BASE) as respx_mock:
            respx_mock.get("/works").mock(
                return_value=Response(200, json=response_json)
            )
            async with openalex_adapter._http_client:
                records = [
                    record
                    async for record in openalex_adapter.fetch_filtered(
                        entity_type="publication",
                        filter_ids=["10.1038/nature12373"],
                        filter_field="doi",
                        limit=1,
                    )
                ]

        assert len(records) == 1
        assert "W2148763428" in records[0]["id"]
        assert records[0]["_lookup_method"] == "doi"

    async def test_doi_not_found(self, openalex_adapter: OpenAlexAdapter) -> None:
        with respx.mock(base_url=OPENALEX_API_BASE) as respx_mock:
            respx_mock.get("/works").mock(
                return_value=Response(200, json={"results": [], "meta": {"count": 0}})
            )
            async with openalex_adapter._http_client:
                records = [
                    record
                    async for record in openalex_adapter.fetch_filtered(
                        entity_type="publication",
                        filter_ids=["10.9999/nonexistent.000"],
                        filter_field="doi",
                    )
                ]

        assert records == []


@pytest.mark.integration
class TestSemanticScholarExternalVerification:
    async def test_doi_batch_found_and_missing(
        self, semanticscholar_adapter: SemanticScholarAdapter
    ) -> None:
        batch_response = [
            {
                "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
                "externalIds": {"DOI": "10.1038/nature12373"},
                "title": "Crystal structure of rhodopsin",
            },
            None,
        ]
        with respx.mock(base_url=SEMANTICSCHOLAR_BASE_URL) as respx_mock:
            respx_mock.post(re.compile(r".*/paper/batch.*")).mock(
                return_value=Response(200, json=batch_response)
            )
            async with semanticscholar_adapter._http_client:
                records = [
                    record
                    async for record in semanticscholar_adapter.fetch_filtered(
                        entity_type="publication",
                        filter_ids=["10.1038/nature12373", "10.9999/nonexistent.000"],
                        filter_field="doi",
                    )
                ]

        assert len(records) == 1
        assert records[0]["externalIds"]["DOI"] == "10.1038/nature12373"
        assert records[0]["_lookup_method"] == "doi"

    async def test_doi_title_fallback(
        self, semanticscholar_adapter: SemanticScholarAdapter
    ) -> None:
        fallback_mapping = {
            "10.9999/nonexistent.000": "Crystal structure of rhodopsin",
        }
        with respx.mock(base_url=SEMANTICSCHOLAR_BASE_URL) as respx_mock:
            respx_mock.post(re.compile(r".*/paper/batch.*")).mock(
                return_value=Response(200, json=[None])
            )
            respx_mock.get("/paper/search").mock(
                return_value=Response(
                    200,
                    json={
                        "data": [
                            {
                                "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
                                "externalIds": {"DOI": "10.1038/nature12373"},
                                "title": "Crystal structure of rhodopsin",
                            }
                        ]
                    },
                )
            )
            async with semanticscholar_adapter._http_client:
                records = [
                    record
                    async for record in semanticscholar_adapter.fetch_filtered_with_fallback(
                        entity_type="publication",
                        filter_ids=["10.9999/nonexistent.000"],
                        filter_field="doi",
                        fallback_mapping=fallback_mapping,
                    )
                ]

        assert len(records) == 1
        assert records[0]["_lookup_method"] == "title_fallback"

    async def test_invalid_entity_type_raises(
        self, semanticscholar_adapter: SemanticScholarAdapter
    ) -> None:
        async with semanticscholar_adapter._http_client:
            with pytest.raises(
                ValueError,
                match="SemanticScholarAdapter supports 'publication' or 'paper'",
            ):
                async for _ in semanticscholar_adapter.fetch(
                    entity_type="dataset",
                    query="Crystal structure of rhodopsin",
                ):
                    continue


@pytest.mark.integration
class TestChEMBLExternalVerification:
    async def test_publication_id_found(self, chembl_adapter: ChemblAdapter) -> None:
        response_json = {
            "documents": [
                {
                    "document_chembl_id": "CHEMBL1614631",
                    "title": "Example ChEMBL publication",
                }
            ],
            "page_meta": {"next": None},
        }
        with respx.mock(base_url=CHEMBL_API_BASE) as respx_mock:
            respx_mock.get("/document").mock(
                return_value=Response(200, json=response_json)
            )
            async with chembl_adapter._http_client:
                records = [
                    record
                    async for record in chembl_adapter.fetch_filtered(
                        entity_type="publication",
                        filter_ids=["CHEMBL1614631"],
                        filter_field="publication_id",
                    )
                ]

        assert len(records) == 1
        assert records[0]["publication_id"] == "CHEMBL1614631"

    async def test_publication_id_not_found(
        self, chembl_adapter: ChemblAdapter
    ) -> None:
        with respx.mock(base_url=CHEMBL_API_BASE) as respx_mock:
            respx_mock.get("/document").mock(
                return_value=Response(
                    200,
                    json={"documents": [], "page_meta": {"next": None}},
                )
            )
            async with chembl_adapter._http_client:
                records = [
                    record
                    async for record in chembl_adapter.fetch_filtered(
                        entity_type="publication",
                        filter_ids=["CHEMBL9999999999"],
                        filter_field="publication_id",
                    )
                ]

        assert records == []
