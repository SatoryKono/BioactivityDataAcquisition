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


@pytest.fixture
def transformer() -> SemanticScholarPublicationTransformer:
    """Create a transformer instance."""
    return SemanticScholarPublicationTransformer()


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
        assert result["year"] == 2024
        assert result["publication_date"] == "2024-05-15"
        assert result["journal"] == "Nature"
        assert result["volume"] == "629"
        assert result["pages"] == "123-130"
        assert result["citation_count"] == 42
        assert result["reference_count"] == 85
        assert result["is_oa"] is True
        assert result["open_access_url"] == "https://example.com/paper.pdf"
        assert result["oa_status"] == "green"  # Normalized to lowercase
        assert result["source"] == "semanticscholar"
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
    async def test_transform_authors_serialized(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Test that authors are serialized as JSON."""
        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        # Authors should be serialized as JSON string
        assert isinstance(result["authors"], str)
        assert "John Doe" in result["authors"]
        assert "Jane Smith" in result["authors"]

    @pytest.mark.asyncio
    async def test_transform_fields_of_study_serialized(
        self,
        transformer: SemanticScholarPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Test that fields_of_study are serialized as JSON."""
        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert isinstance(result["fields_of_study"], str)
        assert "Biology" in result["fields_of_study"]
        assert "Medicine" in result["fields_of_study"]

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
        sample_record["_original_doi"] = "10.1016/invalid.doi"

        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert result["_lookup_method"] == "title_fallback"
        assert result["_original_doi"] == "10.1016/invalid.doi"
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
        assert result["year"] is None

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
        assert result["_run_id"] == "12345678-1234-5678-1234-567812345678"
        assert result["_run_type"] == "incremental"
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
        assert result["year"] is None

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
    async def test_transform_with_pii_hashing(
        self,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Test that author names are hashed when PII hasher is provided."""
        mock_pii_hasher = MagicMock()
        mock_pii_hasher.hash_list = MagicMock(return_value=["hash1", "hash2"])

        transformer = SemanticScholarPublicationTransformer(pii_hasher=mock_pii_hasher)

        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        mock_pii_hasher.hash_list.assert_called_once()
        # Authors should contain hashed values
        assert "hash1" in result["authors"]
        assert "hash2" in result["authors"]
