# tests/unit/application/pipelines/semanticscholar/test_transformer.py
"""Unit tests for Semantic Scholar Publication Transformer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.application.pipelines.semanticscholar.transformer import (
    SemanticScholarPublicationTransformer,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import instantiate_test_transformer

pytestmark = pytest.mark.usefixtures("publication_type_classification_data")


@pytest.fixture
def transformer() -> SemanticScholarPublicationTransformer:
    """Create a transformer instance."""
    return instantiate_test_transformer(SemanticScholarPublicationTransformer)


@pytest.fixture
def mock_context() -> PipelineContext:
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.info = MagicMock()
    mock_logger.warning = MagicMock()
    mock_logger.debug = MagicMock()

    return PipelineContext(
        run_id=UUID("12345678-1234-5678-1234-567812345678"),
        run_type=RunType.INCREMENTAL,
        started_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        logger=mock_logger,
    )


@pytest.fixture
def sample_record() -> dict[str, Any]:
    """Create a sample Semantic Scholar record."""
    return {
        "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
        "externalIds": {
            "DOI": "10.1038/s41586-024-07487-w",
            "PubMed": "12345678",
            "CorpusId": 123456,
        },
        "title": "CRISPR-Cas9 gene editing in human embryos",
        "abstract": "This study demonstrates novel applications...",
        "year": 2024,
        "publicationDate": "2024-05-15",
        "venue": "Nature",
        "journal": {
            "name": "Nature",
            "volume": "629",
            "pages": "123-130",
        },
        "authors": [
            {"authorId": "1234567", "name": "John Doe"},
            {"authorId": "7654321", "name": "Jane Smith"},
        ],
        "citationCount": 42,
        "referenceCount": 85,
        "isOpenAccess": True,
        "openAccessPdf": {
            "url": "https://example.com/paper.pdf",
            "status": "GREEN",
        },
        "tldr": {
            "model": "tldr@v2.0.0",
            "text": "This paper presents a novel approach to gene editing...",
        },
        "fieldsOfStudy": ["Biology", "Medicine"],
        "publicationTypes": ["JournalArticle"],
        "_lookup_method": "doi",
    }


class TestSemanticScholarPublicationTransformer:
    """Tests for SemanticScholarPublicationTransformer."""

    @pytest.mark.asyncio
    async def test_transform_full_record(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Test transforming a complete record."""
        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert result["paper_id"] == "649def34f8be52c8b66281af98ae884c09aef38b"
        assert result["doi"] == "10.1038/s41586-024-07487-w"
        assert result["pmid"] == "12345678"
        assert result["corpus_id"] == 123456
        assert result["title"] == "CRISPR-Cas9 gene editing in human embryos"
        assert result["abstract"] == "This study demonstrates novel applications..."
        assert result["publication_year"] == 2024
        assert result["publication_date"] == "2024-05-15"
        assert result["journal"] == "Nature"
        assert result["issn"] is None
        assert result["issn_list"] is None
        assert result["volume"] == "629"
        assert result["page_range"] == "123-130"
        assert result["citations_received"] == 42
        assert result["citations_made"] == 85
        assert result["is_oa"] is True
        assert result["open_access_url"] == "https://example.com/paper.pdf"
        assert result["oa_status"] == "green"  # Normalized to lowercase
        assert result["publication_type"] == "JournalArticle"
        assert result["publication_type_unified"] == "Journal Article"
        assert result["_source"] == "semanticscholar"
        assert result["_lookup_method"] == "doi"

    @pytest.mark.asyncio
    async def test_transform_tldr_extraction(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Test TLDR field extraction."""
        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert (
            result["tldr"] == "This paper presents a novel approach to gene editing..."
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("abstract_value", [None, "   "])
    async def test_transform_abstract_fallback_from_tldr(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
        abstract_value: str | None,
    ) -> None:
        """Test that abstract falls back to TLDR when missing/empty."""
        sample_record["abstract"] = abstract_value

        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert (
            result["abstract"]
            == "This paper presents a novel approach to gene editing..."
        )
        assert (
            result["tldr"] == "This paper presents a novel approach to gene editing..."
        )

    @pytest.mark.asyncio
    async def test_transform_authors_present(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Test that authors field is present in silver record."""
        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert "authors" in result

    @pytest.mark.asyncio
    async def test_transform_subject_fields_serialized(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Test that subject_fields are serialized as JSON."""
        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert isinstance(result["subject_fields"], str)
        assert "Biology" in result["subject_fields"]
        assert "Medicine" in result["subject_fields"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("publication_types", [None, []])
    async def test_transform_publication_type_empty(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
        publication_types: list[str] | None,
    ) -> None:
        """Test that publication_type defaults to 'publication' when publicationTypes is empty/null."""
        if publication_types is None:
            sample_record.pop("publicationTypes", None)
        else:
            sample_record["publicationTypes"] = publication_types

        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert result["publication_type"] == "PUBLICATION"
        assert result["publication_type_unified"] is None

    @pytest.mark.asyncio
    async def test_transform_publication_type_joined(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Test that publication_type preserves joined raw list values."""
        sample_record["publicationTypes"] = ["JournalArticle", "Review"]

        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert result["publication_type"] == "JournalArticle|Review"
        assert result["publication_type_unified"] == "Review"

    @pytest.mark.asyncio
    async def test_transform_missing_paper_id_skips_record(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that records without paper_id are skipped."""
        record = {
            "title": "Some Title",
            "_lookup_method": "title_fallback",
        }

        result = await transformer.transform(mock_context, record, 0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_title_fallback_record(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Test transforming a record found via title fallback."""
        sample_record["_lookup_method"] = "title_fallback"
        sample_record["_original_id"] = "10.1016/invalid.doi"

        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert result["_lookup_method"] == "title_fallback"
        assert result["_original_id"] == "10.1016/invalid.doi"
        # Should log fallback usage
        mock_context.logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_transform_title_only_record(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Test transforming a record found via title-only search."""
        sample_record["_lookup_method"] = "title_only"
        del sample_record["externalIds"]  # No DOI

        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert result["_lookup_method"] == "title_only"
        assert result["doi"] is None

    @pytest.mark.asyncio
    async def test_transform_minimal_record(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test transforming a minimal record with only required fields."""
        record = {
            "paperId": "a" * 40,  # 40-char hex ID
            "title": "Minimal Paper",
            "_lookup_method": "doi",
        }

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["paper_id"] == "a" * 40
        assert result["title"] == "Minimal Paper"
        assert result["doi"] is None
        assert result["abstract"] is None
        assert result["publication_year"] is None

    @pytest.mark.asyncio
    async def test_transform_content_hash_generated(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Test that content hash is generated."""
        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert "content_hash" in result
        assert len(result["content_hash"]) == 64  # SHA256 hex

    @pytest.mark.asyncio
    async def test_transform_entity_id_generated(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Test that entity ID is generated."""
        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert "entity_id" in result
        assert "semanticscholar" in result["entity_id"]

    @pytest.mark.asyncio
    async def test_transform_lineage_fields_added(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Test that lineage fields are added.

        Note: _dq_warn and _dq_error are added later in the pipeline
        (record processor level), not in the transformer itself.
        This aligns with the OpenAlex transformer pattern.
        """
        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert "_run_id" in result
        assert "_run_type" in result
        assert result["_index"] == 0

    @pytest.mark.asyncio
    async def test_transform_invalid_year_filtered(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Test that invalid years are filtered to None."""
        sample_record["year"] = 3000  # Invalid future year

        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert result["publication_year"] is None

    @pytest.mark.asyncio
    async def test_transform_closed_access(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Test handling of closed access publications."""
        sample_record["isOpenAccess"] = False
        sample_record["openAccessPdf"] = None

        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert result["is_oa"] is False
        assert result["open_access_url"] is None
        assert result["oa_status"] == "closed"  # Now returns "closed" for non-OA


class TestTransformerWithPiiHasher:
    """Tests for transformer with PII hasher."""

    @pytest.mark.asyncio
    async def test_transform_with_pii_hasher(
        self,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Test that transformer applies PII hasher to authors."""
        mock_pii_hasher = MagicMock()
        mock_pii_hasher.hash_list = MagicMock(return_value=["hash1", "hash2"])

        transformer = instantiate_test_transformer(
            SemanticScholarPublicationTransformer,
            pii_hasher=mock_pii_hasher,
        )

        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert "authors" in result


class TestSemanticScholarDoiNormalization:
    """Tests for DOI normalization in Semantic Scholar transformer."""

    @pytest.fixture
    def transformer(self) -> SemanticScholarPublicationTransformer:
        """Create a transformer instance."""
        return instantiate_test_transformer(SemanticScholarPublicationTransformer)

    @staticmethod
    def _make_record_with_doi(doi: str | None) -> dict[str, Any]:
        """Create a Semantic Scholar record with a specific DOI."""
        external_ids = {"CorpusId": 123456}
        if doi is not None:
            external_ids["DOI"] = doi
        return {
            "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
            "externalIds": external_ids,
            "title": "DOI Normalization Test",
            "_lookup_method": "doi",
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "raw_doi,expected",
        [
            ("10.1038/NATURE12373", "10.1038/nature12373"),
            ("10.1038/nature12373", "10.1038/nature12373"),
            ("  10.1000/xyz  ", "10.1000/xyz"),
            ("10.1000/ABC.DEF", "10.1000/abc.def"),
            ("10.1000/Test-DOI_123", "10.1000/test-doi_123"),
        ],
    )
    async def test_doi_normalization_lowercase_and_strip(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        raw_doi: str,
        expected: str,
    ) -> None:
        """Test that DOIs are normalized to lowercase and stripped."""
        record = self._make_record_with_doi(raw_doi)

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["doi"] == expected

    @pytest.mark.asyncio
    async def test_doi_normalization_none_handling(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that None DOI remains None."""
        record = self._make_record_with_doi(None)

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["doi"] is None

    @pytest.mark.asyncio
    async def test_doi_normalization_affects_content_hash(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that DOIs with different cases produce same content hash after normalization."""
        record_upper = self._make_record_with_doi("10.1038/NATURE12373")
        record_lower = self._make_record_with_doi("10.1038/nature12373")

        result_upper = await transformer.transform(mock_context, record_upper, 0)
        result_lower = await transformer.transform(mock_context, record_lower, 0)

        assert result_upper is not None
        assert result_lower is not None
        # After normalization, content hashes should be identical
        assert result_upper["content_hash"] == result_lower["content_hash"]


class TestSemanticScholarPmidNormalization:
    """Tests for PMID normalization in Semantic Scholar transformer.

    PubMedId.from_raw() strips leading zeros, converts int→str, and
    validates upper bound (< 10^10).
    """

    @pytest.fixture
    def transformer(self) -> SemanticScholarPublicationTransformer:
        """Create a transformer instance."""
        return instantiate_test_transformer(SemanticScholarPublicationTransformer)

    @staticmethod
    def _make_record_with_pmid(pmid: str | None) -> dict[str, Any]:
        """Create a Semantic Scholar record with a specific PMID."""
        external_ids: dict[str, Any] = {"CorpusId": 123456}
        if pmid is not None:
            external_ids["PubMed"] = pmid
        return {
            "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
            "externalIds": external_ids,
            "title": "PMID Normalization Test",
            "_lookup_method": "doi",
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "raw_pmid,expected",
        [
            ("12345", "12345"),
            ("0012345", "12345"),
            ("00001", "1"),
            ("9999999999", "9999999999"),
        ],
    )
    async def test_pmid_normalization(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        raw_pmid: str,
        expected: str,
    ) -> None:
        """Test that PMIDs are normalized (leading zeros stripped)."""
        record = self._make_record_with_pmid(raw_pmid)

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["pmid"] == expected

    @pytest.mark.asyncio
    async def test_pmid_none_handling(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that None PMID remains None."""
        record = self._make_record_with_pmid(None)

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["pmid"] is None

    @pytest.mark.asyncio
    async def test_pmid_exceeds_upper_bound(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that PMID >= 10^10 is normalized to None."""
        record = self._make_record_with_pmid("10000000000")

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["pmid"] is None


class TestSemanticScholarDateNormalization:
    """Tests for publication_date normalization in Semantic Scholar transformer.

    Semantic Scholar API may return partial dates (YYYY or YYYY-MM).
    The transformer normalizes them to full ISO dates using end-of-period.
    """

    @pytest.fixture
    def transformer(self) -> SemanticScholarPublicationTransformer:
        """Create a transformer instance."""
        return instantiate_test_transformer(SemanticScholarPublicationTransformer)

    @staticmethod
    def _make_record_with_date(date_str: str | None) -> dict[str, Any]:
        """Create a Semantic Scholar record with a specific publication date."""
        record: dict[str, Any] = {
            "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
            "title": "Date Normalization Test",
            "_lookup_method": "doi",
        }
        if date_str is not None:
            record["publicationDate"] = date_str
        return record

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "raw_date,expected",
        [
            # Full ISO date - unchanged
            ("2024-05-15", "2024-05-15"),
            ("2020-01-01", "2020-01-01"),
            ("1999-12-31", "1999-12-31"),
            # Year-month only -> last day of month
            ("2024-05", "2024-05-31"),
            ("2020-01", "2020-01-31"),
            ("1999-12", "1999-12-31"),
            # Year only -> December 31
            ("2024", "2024-12-31"),
            ("2020", "2020-12-31"),
            ("1999", "1999-12-31"),
        ],
    )
    async def test_publication_date_normalization(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        raw_date: str,
        expected: str,
    ) -> None:
        """Test that partial dates are normalized to full ISO dates."""
        record = self._make_record_with_date(raw_date)

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["publication_date"] == expected

    @pytest.mark.asyncio
    async def test_publication_date_none_handling(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that None publication_date remains None."""
        record = self._make_record_with_date(None)

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["publication_date"] is None

    @pytest.mark.asyncio
    async def test_publication_date_empty_string(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that empty string publication_date becomes None."""
        record = self._make_record_with_date("")

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["publication_date"] is None

    @pytest.mark.asyncio
    async def test_publication_date_whitespace_only(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that whitespace-only publication_date becomes None."""
        record = self._make_record_with_date("   ")

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["publication_date"] is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_date",
        [
            "invalid",
            "2024/05/15",  # Wrong separator
            "15-05-2024",  # Wrong order
            "2024-5-15",  # Missing zero-padding
            "20240515",  # No separators
        ],
    )
    async def test_publication_date_invalid_format(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        invalid_date: str,
    ) -> None:
        """Test that invalid date formats become None."""
        record = self._make_record_with_date(invalid_date)

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["publication_date"] is None

    @pytest.mark.asyncio
    async def test_publication_date_with_whitespace(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that dates with surrounding whitespace are stripped and normalized."""
        record = self._make_record_with_date("  2024-05  ")

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["publication_date"] == "2024-05-31"


class TestSemanticScholarUnifiedPageFields:
    """Tests for unified page field parsing (page_first, page_last).

    Note: The parse_page_range function tests are in tests/unit/domain/test_normalization.py.
    These tests verify the integration with the transformer.
    """

    @pytest.fixture
    def transformer(self) -> SemanticScholarPublicationTransformer:
        """Create a transformer instance."""
        return instantiate_test_transformer(SemanticScholarPublicationTransformer)

    @pytest.mark.asyncio
    async def test_unified_page_fields_in_transform(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Test that unified page fields are present in transformed output."""
        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        # sample_record has journal.pages = "123-130"
        assert result["page_range"] == "123-130"
        assert result["page_first"] == "123"
        assert result["page_last"] == "130"

    @pytest.mark.asyncio
    async def test_unified_page_fields_no_pages(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test unified page fields when no pages in record."""
        record = {
            "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
            "title": "Test Paper",
            "year": 2024,
        }

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["page_range"] is None
        assert result["page_first"] is None
        assert result["page_last"] is None


class TestSemanticScholarNewFields:
    """Tests for newly added fields (dblp_id, influential_citation_count)."""

    @pytest.fixture
    def transformer(self) -> SemanticScholarPublicationTransformer:
        """Create a transformer instance."""
        return instantiate_test_transformer(SemanticScholarPublicationTransformer)

    @pytest.fixture
    def mock_context(self) -> PipelineContext:
        """Create a mock pipeline context."""
        mock_logger = MagicMock()
        mock_logger.info = MagicMock()
        mock_logger.warning = MagicMock()
        mock_logger.debug = MagicMock()

        return PipelineContext(
            run_id=UUID("12345678-1234-5678-1234-567812345678"),
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
            logger=mock_logger,
        )

    @pytest.mark.asyncio
    async def test_dblp_id_extraction(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test DBLP ID is extracted from externalIds."""
        record = {
            "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
            "externalIds": {
                "DOI": "10.1145/12345",
                "DBLP": "journals/cacm/Smith24",
            },
            "title": "Test Paper",
            "_lookup_method": "doi",
        }

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["dblp_id"] == "journals/cacm/Smith24"

    @pytest.mark.asyncio
    async def test_dblp_id_none_when_missing(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test DBLP ID is None when not present in externalIds."""
        record = {
            "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
            "externalIds": {"DOI": "10.1145/12345"},
            "title": "Test Paper",
            "_lookup_method": "doi",
        }

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["dblp_id"] is None

    @pytest.mark.asyncio
    async def test_influential_citation_count_extraction(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test influentialCitationCount is extracted."""
        record = {
            "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
            "title": "Test Paper",
            "citationCount": 100,
            "referenceCount": 50,
            "influentialCitationCount": 25,
            "_lookup_method": "doi",
        }

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["citations_received"] == 100
        assert result["citations_made"] == 50
        assert result["influential_citation_count"] == 25

    @pytest.mark.asyncio
    async def test_influential_citation_count_none_when_missing(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test influentialCitationCount is None when not present."""
        record = {
            "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
            "title": "Test Paper",
            "citationCount": 100,
            "_lookup_method": "doi",
        }

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["citations_received"] == 100
        assert result["influential_citation_count"] is None

    @pytest.mark.asyncio
    async def test_influential_citation_count_zero(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test influentialCitationCount of 0 is preserved (not treated as None)."""
        record = {
            "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
            "title": "Test Paper",
            "citationCount": 10,
            "influentialCitationCount": 0,
            "_lookup_method": "doi",
        }

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["citations_received"] == 10
        assert result["influential_citation_count"] == 0
