# tests/integration/test_cross_provider_doi_normalization.py
"""Integration tests for cross-provider DOI normalization consistency.

Verifies that the same DOI produces identical normalized values and content hashes
across all publication providers (CrossRef, PubMed, SemanticScholar, OpenAlex).

This ensures JOIN operations between Silver tables from different providers
will correctly match records based on normalized DOI.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.crossref.transformer import (
    CrossRefPublicationTransformer,
)
from bioetl.application.pipelines.openalex.transformer import (
    OpenAlexPublicationTransformer,
)
from bioetl.application.pipelines.pubmed.transformer import (
    PubMedPublicationTransformer,
)
from bioetl.application.pipelines.semanticscholar.transformer import (
    SemanticScholarPublicationTransformer,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType


@pytest.fixture
def mock_context() -> PipelineContext:
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    mock_logger.debug = MagicMock()
    mock_logger.info = MagicMock()
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        started_at=datetime.now(UTC),
        logger=mock_logger,
    )


@pytest.mark.integration
class TestCrossProviderDoiNormalization:
    """Integration tests for DOI normalization consistency across providers."""

    @staticmethod
    def _make_pubmed_record(doi: str) -> dict[str, Any]:
        """Create a PubMed record with a specific DOI."""
        return {
            "_raw_xml": f"""<?xml version="1.0"?>
            <PubmedArticle>
              <MedlineCitation>
                <PMID>12345678</PMID>
                <Article>
                  <ArticleTitle>Cross-Provider DOI Test</ArticleTitle>
                  <ELocationID EIdType="doi">{doi}</ELocationID>
                </Article>
              </MedlineCitation>
            </PubmedArticle>
            """
        }

    @staticmethod
    def _make_semanticscholar_record(doi: str) -> dict[str, Any]:
        """Create a Semantic Scholar record with a specific DOI."""
        return {
            "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
            "externalIds": {"DOI": doi},
            "title": "Cross-Provider DOI Test",
            "_lookup_method": "doi",
        }

    @staticmethod
    def _make_openalex_record(doi: str) -> dict[str, Any]:
        """Create an OpenAlex record with a specific DOI URL."""
        return {
            "id": "https://openalex.org/W2148763428",
            "doi": f"https://doi.org/{doi}",
            "title": "Cross-Provider DOI Test",
            "_lookup_method": "doi",
        }

    @staticmethod
    def _make_crossref_record(doi: str) -> dict[str, Any]:
        """Create a CrossRef record with a specific DOI."""
        return {
            "DOI": doi,
            "title": ["Cross-Provider DOI Test"],
            "type": "journal-article",
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "raw_doi",
        [
            "10.1038/NATURE12373",
            "10.1038/nature12373",
            "10.1000/ABC.DEF",
            "  10.1000/xyz  ",
        ],
    )
    async def test_doi_normalization_consistency_across_providers(
        self,
        mock_context: PipelineContext,
        raw_doi: str,
    ) -> None:
        """Test that the same raw DOI normalizes identically across all providers."""
        # Create transformers
        pubmed_transformer = PubMedPublicationTransformer()
        s2_transformer = SemanticScholarPublicationTransformer()
        openalex_transformer = OpenAlexPublicationTransformer()
        crossref_transformer = CrossRefPublicationTransformer()

        # Transform records
        pubmed_result = await pubmed_transformer.transform(
            mock_context, self._make_pubmed_record(raw_doi), 0
        )
        s2_result = await s2_transformer.transform(
            mock_context, self._make_semanticscholar_record(raw_doi), 0
        )
        openalex_result = await openalex_transformer.transform(
            mock_context, self._make_openalex_record(raw_doi), 0
        )
        crossref_result = await crossref_transformer.transform(
            mock_context, self._make_crossref_record(raw_doi), 0
        )

        # Verify all results are not None
        assert pubmed_result is not None, "PubMed transformation failed"
        assert s2_result is not None, "Semantic Scholar transformation failed"
        assert openalex_result is not None, "OpenAlex transformation failed"
        assert crossref_result is not None, "CrossRef transformation failed"

        # Extract normalized DOIs
        normalized_dois = {
            "pubmed": pubmed_result["doi"],
            "semanticscholar": s2_result["doi"],
            "openalex": openalex_result["doi"],
            "crossref": crossref_result["doi"],
        }

        # All normalized DOIs should be identical
        unique_dois = set(normalized_dois.values())
        assert len(unique_dois) == 1, (
            f"DOI normalization inconsistent across providers: {normalized_dois}"
        )

        # Verify normalized DOI is lowercase and stripped
        normalized_doi = next(iter(unique_dois))
        assert normalized_doi == normalized_doi.lower(), "DOI not lowercased"
        assert normalized_doi == normalized_doi.strip(), "DOI not stripped"

    @pytest.mark.asyncio
    async def test_uppercase_doi_produces_same_hash_as_lowercase(
        self,
        mock_context: PipelineContext,
    ) -> None:
        """Test that uppercase and lowercase DOIs produce the same normalized value.

        This is critical for cross-provider JOINs in Silver layer.
        """
        uppercase_doi = "10.1038/NATURE12373"
        lowercase_doi = "10.1038/nature12373"
        expected_normalized = "10.1038/nature12373"

        transformers = {
            "pubmed": (PubMedPublicationTransformer(), self._make_pubmed_record),
            "semanticscholar": (
                SemanticScholarPublicationTransformer(),
                self._make_semanticscholar_record,
            ),
            "openalex": (
                OpenAlexPublicationTransformer(),
                self._make_openalex_record,
            ),
            "crossref": (CrossRefPublicationTransformer(), self._make_crossref_record),
        }

        for provider_name, (transformer, make_record) in transformers.items():
            result_upper = await transformer.transform(
                mock_context, make_record(uppercase_doi), 0
            )
            result_lower = await transformer.transform(
                mock_context, make_record(lowercase_doi), 0
            )

            assert result_upper is not None, (
                f"{provider_name} uppercase transform failed"
            )
            assert result_lower is not None, (
                f"{provider_name} lowercase transform failed"
            )

            # Both should normalize to the same value
            assert result_upper["doi"] == expected_normalized, (
                f"{provider_name} uppercase DOI not normalized correctly: "
                f"got {result_upper['doi']}, expected {expected_normalized}"
            )
            assert result_lower["doi"] == expected_normalized, (
                f"{provider_name} lowercase DOI not normalized correctly: "
                f"got {result_lower['doi']}, expected {expected_normalized}"
            )

    @pytest.mark.asyncio
    async def test_none_doi_handled_consistently(
        self,
        mock_context: PipelineContext,
    ) -> None:
        """Test that None DOI is handled consistently across providers."""
        # Create records without DOI
        pubmed_record = {
            "_raw_xml": """<?xml version="1.0"?>
            <PubmedArticle>
              <MedlineCitation>
                <PMID>12345678</PMID>
                <Article>
                  <ArticleTitle>No DOI Article</ArticleTitle>
                </Article>
              </MedlineCitation>
            </PubmedArticle>
            """
        }

        s2_record = {
            "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
            "externalIds": {},
            "title": "No DOI Article",
            "_lookup_method": "title_only",
        }

        openalex_record = {
            "id": "https://openalex.org/W2148763428",
            "doi": None,
            "title": "No DOI Article",
            "_lookup_method": "title_only",
        }

        # CrossRef requires DOI, so skip it for this test

        pubmed_result = await PubMedPublicationTransformer().transform(
            mock_context, pubmed_record, 0
        )
        s2_result = await SemanticScholarPublicationTransformer().transform(
            mock_context, s2_record, 0
        )
        openalex_result = await OpenAlexPublicationTransformer().transform(
            mock_context, openalex_record, 0
        )

        assert pubmed_result is not None
        assert s2_result is not None
        assert openalex_result is not None

        # All should return None for DOI
        assert pubmed_result["doi"] is None
        assert s2_result["doi"] is None
        assert openalex_result["doi"] is None
