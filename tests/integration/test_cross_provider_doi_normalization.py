# tests/integration/test_cross_provider_doi_normalization.py
"""Integration tests for cross-provider DOI normalization consistency.

Verifies two related invariants for publication providers
(CrossRef, PubMed, SemanticScholar, OpenAlex):
- the same DOI normalizes to the same canonical value across providers
- normalization-equivalent DOI inputs produce the same final provider-local
  content hash after staged Silver finalization

This ensures JOIN operations between Silver tables from different providers
will correctly match records based on normalized DOI, while respecting the
hashing contract that includes provider identity.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
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
from tests.helpers.transformer_dependencies import instantiate_test_transformer


def _legacy_http_url(path: str) -> str:
    return "http" + "://" + path


@pytest.fixture
def mock_context() -> PipelineContext:
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    mock_logger.debug = MagicMock()
    mock_logger.info = MagicMock()
    return PipelineContext(
        run_id=deterministic_uuid_from_callsite(
            "test_cross_provider_doi_normalization"
        ),
        run_type=RunType.INCREMENTAL,
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        logger=mock_logger,
    )


@pytest.mark.integration
class TestCrossProviderDoiNormalization:
    """Integration tests for DOI normalization consistency across providers."""

    @staticmethod
    async def _finalize_publication_record(
        transformer: Any,
        provider: str,
        context: PipelineContext,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """Run the staged publication path through normalization and final hash."""
        pre_silver = await transformer.transform_pre_silver(context, record, 0)
        assert pre_silver is not None, f"{provider} pre-silver transformation failed"
        finalized = RecordNormalizationProcessor(provider=provider).finalize_pre_silver(
            pre_silver,
            context,
            0,
        )
        assert finalized is not None, f"{provider} Silver finalization failed"
        return finalized

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
        pubmed_transformer = instantiate_test_transformer(PubMedPublicationTransformer)
        s2_transformer = instantiate_test_transformer(
            SemanticScholarPublicationTransformer
        )
        openalex_transformer = instantiate_test_transformer(
            OpenAlexPublicationTransformer
        )
        crossref_transformer = instantiate_test_transformer(
            CrossRefPublicationTransformer
        )

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
        """Normalization-equivalent DOI inputs must converge before final hash.

        Hash equality is asserted per provider because provider identity is part of
        the content-hash contract.
        """
        uppercase_doi = "10.1038/NATURE12373"
        lowercase_doi = "10.1038/nature12373"
        expected_normalized = "10.1038/nature12373"

        transformers = {
            "pubmed": (
                instantiate_test_transformer(PubMedPublicationTransformer),
                self._make_pubmed_record,
            ),
            "semanticscholar": (
                instantiate_test_transformer(SemanticScholarPublicationTransformer),
                self._make_semanticscholar_record,
            ),
            "openalex": (
                instantiate_test_transformer(OpenAlexPublicationTransformer),
                self._make_openalex_record,
            ),
            "crossref": (
                instantiate_test_transformer(CrossRefPublicationTransformer),
                self._make_crossref_record,
            ),
        }

        for provider_name, (transformer, make_record) in transformers.items():
            result_upper = await self._finalize_publication_record(
                transformer,
                provider_name,
                mock_context,
                make_record(uppercase_doi),
            )
            result_lower = await self._finalize_publication_record(
                transformer,
                provider_name,
                mock_context,
                make_record(lowercase_doi),
            )

            assert result_upper["doi"] == expected_normalized, (
                f"{provider_name} uppercase DOI not normalized correctly: "
                f"got {result_upper['doi']}, expected {expected_normalized}"
            )
            assert result_lower["doi"] == expected_normalized, (
                f"{provider_name} lowercase DOI not normalized correctly: "
                f"got {result_lower['doi']}, expected {expected_normalized}"
            )
            assert result_upper["content_hash"] == result_lower["content_hash"], (
                f"{provider_name} final content hash diverged for normalization-"
                "equivalent DOI inputs"
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

        pubmed_result = await instantiate_test_transformer(
            PubMedPublicationTransformer
        ).transform(mock_context, pubmed_record, 0)
        s2_result = await instantiate_test_transformer(
            SemanticScholarPublicationTransformer
        ).transform(mock_context, s2_record, 0)
        openalex_result = await instantiate_test_transformer(
            OpenAlexPublicationTransformer
        ).transform(mock_context, openalex_record, 0)

        assert pubmed_result is not None
        assert s2_result is not None
        assert openalex_result is not None

        # All should return None for DOI
        assert pubmed_result["doi"] is None
        assert s2_result["doi"] is None
        assert openalex_result["doi"] is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "url_prefixed_doi,expected_normalized",
        [
            ("https://doi.org/10.1234/test", "10.1234/test"),
            ("https://doi.org/10.1038/NATURE12373", "10.1038/nature12373"),
            (_legacy_http_url("doi.org/10.1000/ABC.DEF"), "10.1000/abc.def"),
            ("doi:10.5555/Mixed.Case", "10.5555/mixed.case"),
        ],
    )
    async def test_url_prefixed_doi_stripped_across_providers(
        self,
        mock_context: PipelineContext,
        url_prefixed_doi: str,
        expected_normalized: str,
    ) -> None:
        """Test that URL-prefixed DOIs are stripped and normalized across providers.

        Each provider receives a DOI with URL prefix (e.g., https://doi.org/...)
        and the Silver output must contain the bare, lowercase DOI.
        """
        # Build records with the URL-prefixed DOI placed directly in each
        # provider's DOI field (bypassing helpers that may add their own prefix)
        pubmed_record: dict[str, Any] = {
            "_raw_xml": f"""<?xml version="1.0"?>
            <PubmedArticle>
              <MedlineCitation>
                <PMID>99999999</PMID>
                <Article>
                  <ArticleTitle>URL Prefix DOI Test</ArticleTitle>
                  <ELocationID EIdType="doi">{url_prefixed_doi}</ELocationID>
                </Article>
              </MedlineCitation>
            </PubmedArticle>
            """
        }
        s2_record: dict[str, Any] = {
            "paperId": "a" * 40,
            "externalIds": {"DOI": url_prefixed_doi},
            "title": "URL Prefix DOI Test",
            "_lookup_method": "doi",
        }
        openalex_record: dict[str, Any] = {
            "id": "https://openalex.org/W9999999999",
            "doi": url_prefixed_doi,
            "title": "URL Prefix DOI Test",
            "_lookup_method": "doi",
        }

        pubmed_result = await instantiate_test_transformer(
            PubMedPublicationTransformer
        ).transform(mock_context, pubmed_record, 0)
        s2_result = await instantiate_test_transformer(
            SemanticScholarPublicationTransformer
        ).transform(mock_context, s2_record, 0)
        openalex_result = await instantiate_test_transformer(
            OpenAlexPublicationTransformer
        ).transform(mock_context, openalex_record, 0)

        assert pubmed_result is not None, "PubMed URL-prefix transform failed"
        assert s2_result is not None, "Semantic Scholar URL-prefix transform failed"
        assert openalex_result is not None, "OpenAlex URL-prefix transform failed"

        assert pubmed_result["doi"] == expected_normalized, (
            f"PubMed did not strip URL prefix: {pubmed_result['doi']}"
        )
        assert s2_result["doi"] == expected_normalized, (
            f"Semantic Scholar did not strip URL prefix: {s2_result['doi']}"
        )
        assert openalex_result["doi"] == expected_normalized, (
            f"OpenAlex did not strip URL prefix: {openalex_result['doi']}"
        )
