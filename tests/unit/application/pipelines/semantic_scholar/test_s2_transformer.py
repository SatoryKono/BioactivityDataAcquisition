"""Unit tests for Semantic Scholar Publication Transformer."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.semantic_scholar.transformer import (
    S2PublicationTransformer,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType


@pytest.fixture
def mock_context():
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestS2PublicationTransformer:
    """Tests for S2PublicationTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create S2PublicationTransformer instance."""
        return S2PublicationTransformer(provider="semantic_scholar")

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid paper record with all fields."""
        record = {
            "paperId": "abc123def456789012345678901234567890abcd",
            "externalIds": {
                "DOI": "10.1038/nature12373",
                "PubMed": "23903654",
            },
            "title": "A Machine Learning Approach to Drug Discovery",
            "authors": [
                {"authorId": "123", "name": "John Doe"},
                {"authorId": "456", "name": "Jane Smith"},
            ],
            "venue": "Nature",
            "year": 2023,
            "abstract": "This paper describes a novel approach...",
            "citationCount": 100,
            "influentialCitationCount": 25,
            "fieldsOfStudy": ["Computer Science", "Biology"],
            "embedding": {"model": "specter", "vector": [0.1, 0.2, 0.3]},
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["semantic_scholar_id"] == "abc123def456789012345678901234567890abcd"
        assert result["doi"] == "10.1038/nature12373"
        assert result["pmid"] == 23903654
        assert result["title"] == "A Machine Learning Approach to Drug Discovery"
        assert result["authors"] == ["John Doe", "Jane Smith"]
        assert result["journal"] == "Nature"
        assert result["year"] == 2023
        assert result["citation_count"] == 100
        assert result["influential_citation_count"] == 25
        assert result["fields_of_study"] == ["Computer Science", "Biology"]
        assert result["_embedding"] == [0.1, 0.2, 0.3]
        # Lineage fields should be present
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_ingestion_ts" in result

    @pytest.mark.asyncio
    async def test_transform_missing_paper_id(self, transformer, mock_context):
        """Test transformation returns None when paperId is missing."""
        record = {
            "title": "Some Paper",
            "authors": [],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_minimal_valid_record(self, transformer, mock_context):
        """Test transformation with minimal valid record (only paperId)."""
        record = {
            "paperId": "abc123def456789012345678901234567890abcd",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["semantic_scholar_id"] == "abc123def456789012345678901234567890abcd"
        assert result["doi"] is None
        assert result["pmid"] is None
        assert result["title"] is None
        assert result["authors"] == []
        assert result["fields_of_study"] == []
        assert result["_embedding"] == []

    @pytest.mark.asyncio
    async def test_transform_doi_normalized_to_lowercase(self, transformer, mock_context):
        """Test that DOI is normalized to lowercase."""
        record = {
            "paperId": "abc123def456789012345678901234567890abcd",
            "externalIds": {
                "DOI": "10.1038/NATURE12373",
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["doi"] == "10.1038/nature12373"

    @pytest.mark.asyncio
    async def test_transform_pmid_as_string(self, transformer, mock_context):
        """Test that string PMID is converted to integer."""
        record = {
            "paperId": "abc123def456789012345678901234567890abcd",
            "externalIds": {
                "PubMed": "12345678",
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["pmid"] == 12345678
        assert isinstance(result["pmid"], int)

    @pytest.mark.asyncio
    async def test_transform_pmid_as_int(self, transformer, mock_context):
        """Test that integer PMID is preserved."""
        record = {
            "paperId": "abc123def456789012345678901234567890abcd",
            "externalIds": {
                "PubMed": 12345678,
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["pmid"] == 12345678

    @pytest.mark.asyncio
    async def test_transform_entity_id_format(self, transformer, mock_context):
        """Test that entity_id follows expected format."""
        record = {
            "paperId": "abc123def456789012345678901234567890abcd",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "entity_id" in result
        # Entity ID should contain provider and paper_id
        assert "semantic_scholar" in result["entity_id"]

    @pytest.mark.asyncio
    async def test_transform_content_hash_generated(self, transformer, mock_context):
        """Test that content_hash is generated and is consistent."""
        record = {
            "paperId": "abc123def456789012345678901234567890abcd",
            "title": "Test Paper",
        }

        result1 = await transformer.transform(mock_context, record, index=0)
        result2 = await transformer.transform(mock_context, record, index=0)

        assert result1 is not None
        assert result2 is not None
        assert "content_hash" in result1
        assert "content_hash" in result2
        assert result1["content_hash"] == result2["content_hash"]

    @pytest.mark.asyncio
    async def test_transform_content_hash_excludes_embedding(
        self, transformer, mock_context
    ):
        """Test that content hash excludes _embedding field."""
        record1 = {
            "paperId": "abc123def456789012345678901234567890abcd",
            "title": "Test Paper",
            "embedding": {"vector": [0.1, 0.2, 0.3]},
        }
        record2 = {
            "paperId": "abc123def456789012345678901234567890abcd",
            "title": "Test Paper",
            "embedding": {"vector": [0.9, 0.8, 0.7]},  # Different embedding
        }

        result1 = await transformer.transform(mock_context, record1, index=0)
        result2 = await transformer.transform(mock_context, record2, index=0)

        assert result1 is not None
        assert result2 is not None
        # Content hash should be the same (embedding excluded)
        assert result1["content_hash"] == result2["content_hash"]
        # But embeddings should be different
        assert result1["_embedding"] != result2["_embedding"]

    @pytest.mark.asyncio
    async def test_transform_handles_empty_authors(self, transformer, mock_context):
        """Test that empty authors list is handled correctly."""
        record = {
            "paperId": "abc123def456789012345678901234567890abcd",
            "authors": [],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["authors"] == []

    @pytest.mark.asyncio
    async def test_transform_filters_invalid_authors(self, transformer, mock_context):
        """Test that authors without names are filtered out."""
        record = {
            "paperId": "abc123def456789012345678901234567890abcd",
            "authors": [
                {"authorId": "123", "name": "John Doe"},
                {"authorId": "456"},  # No name
                {"authorId": "789", "name": ""},  # Empty name
                {"authorId": "012", "name": "Jane Smith"},
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["authors"] == ["John Doe", "Jane Smith"]

    @pytest.mark.asyncio
    async def test_transform_handles_null_external_ids(self, transformer, mock_context):
        """Test that null externalIds is handled gracefully."""
        record = {
            "paperId": "abc123def456789012345678901234567890abcd",
            "externalIds": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["doi"] is None
        assert result["pmid"] is None

    @pytest.mark.asyncio
    async def test_transform_handles_null_embedding(self, transformer, mock_context):
        """Test that null embedding is handled gracefully."""
        record = {
            "paperId": "abc123def456789012345678901234567890abcd",
            "embedding": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["_embedding"] == []

    @pytest.mark.asyncio
    async def test_transform_handles_empty_embedding_vector(
        self, transformer, mock_context
    ):
        """Test that empty embedding vector is handled gracefully."""
        record = {
            "paperId": "abc123def456789012345678901234567890abcd",
            "embedding": {"model": "specter", "vector": []},
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["_embedding"] == []

    @pytest.mark.asyncio
    async def test_transform_lineage_fields_present(self, transformer, mock_context):
        """Test that lineage fields are properly added to the result."""
        record = {
            "paperId": "abc123def456789012345678901234567890abcd",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Lineage fields should be present with underscore prefix
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_source_batch_id" in result
        assert "_ingestion_ts" in result
        # Verify types
        assert isinstance(result["_run_id"], str)
        assert isinstance(result["_run_type"], str)
        assert isinstance(result["_ingestion_ts"], str)

    @pytest.mark.asyncio
    async def test_transform_empty_paper_id_rejected(self, transformer, mock_context):
        """Test that empty string paperId is rejected."""
        record = {
            "paperId": "",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_non_string_paper_id_rejected(
        self, transformer, mock_context
    ):
        """Test that non-string paperId is rejected."""
        record = {
            "paperId": 12345,  # Should be string
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None


@pytest.mark.unit
class TestS2PublicationTransformerHelpers:
    """Tests for S2PublicationTransformer helper methods."""

    def test_extract_doi_valid(self):
        """Test DOI extraction with valid DOI."""
        result = S2PublicationTransformer._extract_doi({"DOI": "10.1038/nature12373"})
        assert result == "10.1038/nature12373"

    def test_extract_doi_uppercase_normalized(self):
        """Test DOI extraction normalizes to lowercase."""
        result = S2PublicationTransformer._extract_doi({"DOI": "10.1038/NATURE12373"})
        assert result == "10.1038/nature12373"

    def test_extract_doi_with_whitespace(self):
        """Test DOI extraction strips whitespace."""
        result = S2PublicationTransformer._extract_doi({"DOI": "  10.1038/nature12373  "})
        assert result == "10.1038/nature12373"

    def test_extract_doi_missing(self):
        """Test DOI extraction when DOI is missing."""
        result = S2PublicationTransformer._extract_doi({})
        assert result is None

    def test_extract_doi_none(self):
        """Test DOI extraction when DOI is None."""
        result = S2PublicationTransformer._extract_doi({"DOI": None})
        assert result is None

    def test_extract_pmid_string(self):
        """Test PMID extraction from string."""
        result = S2PublicationTransformer._extract_pmid({"PubMed": "12345678"})
        assert result == 12345678

    def test_extract_pmid_int(self):
        """Test PMID extraction from integer."""
        result = S2PublicationTransformer._extract_pmid({"PubMed": 12345678})
        assert result == 12345678

    def test_extract_pmid_missing(self):
        """Test PMID extraction when PMID is missing."""
        result = S2PublicationTransformer._extract_pmid({})
        assert result is None

    def test_extract_pmid_invalid_string(self):
        """Test PMID extraction with non-numeric string."""
        result = S2PublicationTransformer._extract_pmid({"PubMed": "abc123"})
        assert result is None

    def test_extract_authors_valid(self):
        """Test author extraction with valid authors."""
        authors = [
            {"authorId": "123", "name": "John Doe"},
            {"authorId": "456", "name": "Jane Smith"},
        ]
        result = S2PublicationTransformer._extract_authors(authors)
        assert result == ["John Doe", "Jane Smith"]

    def test_extract_authors_filters_empty_names(self):
        """Test author extraction filters empty names."""
        authors = [
            {"authorId": "123", "name": "John Doe"},
            {"authorId": "456", "name": ""},
            {"authorId": "789", "name": "Jane Smith"},
        ]
        result = S2PublicationTransformer._extract_authors(authors)
        assert result == ["John Doe", "Jane Smith"]

    def test_extract_authors_filters_missing_names(self):
        """Test author extraction filters authors without name field."""
        authors = [
            {"authorId": "123", "name": "John Doe"},
            {"authorId": "456"},
            {"authorId": "789", "name": "Jane Smith"},
        ]
        result = S2PublicationTransformer._extract_authors(authors)
        assert result == ["John Doe", "Jane Smith"]

    def test_extract_fields_of_study_valid(self):
        """Test fields of study extraction."""
        result = S2PublicationTransformer._extract_fields_of_study(
            ["Computer Science", "Biology"]
        )
        assert result == ["Computer Science", "Biology"]

    def test_extract_fields_of_study_empty(self):
        """Test fields of study extraction with empty list."""
        result = S2PublicationTransformer._extract_fields_of_study([])
        assert result == []

    def test_extract_fields_of_study_none(self):
        """Test fields of study extraction with None."""
        result = S2PublicationTransformer._extract_fields_of_study(None)
        assert result == []

    def test_extract_embedding_valid(self):
        """Test embedding extraction with valid embedding."""
        result = S2PublicationTransformer._extract_embedding(
            {"model": "specter", "vector": [0.1, 0.2, 0.3]}
        )
        assert result == [0.1, 0.2, 0.3]

    def test_extract_embedding_none(self):
        """Test embedding extraction with None."""
        result = S2PublicationTransformer._extract_embedding(None)
        assert result == []

    def test_extract_embedding_empty_vector(self):
        """Test embedding extraction with empty vector."""
        result = S2PublicationTransformer._extract_embedding(
            {"model": "specter", "vector": []}
        )
        assert result == []

    def test_extract_embedding_missing_vector(self):
        """Test embedding extraction with missing vector field."""
        result = S2PublicationTransformer._extract_embedding({"model": "specter"})
        assert result == []
