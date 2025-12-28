"""Tests for SemanticScholarPaper domain entity."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from bioetl.domain.entities.semantic_scholar import SemanticScholarPaper
from bioetl.domain.types import ContentHash, EntityID, RunID, RunType


@pytest.fixture
def valid_paper_kwargs() -> dict:
    """Create valid kwargs for SemanticScholarPaper."""
    return {
        "entity_id": EntityID("abc123"),
        "content_hash": ContentHash("sha256:abc123def456"),
        "run_id": RunID(uuid4()),
        "run_type": RunType.INCREMENTAL,
        "ingestion_ts": datetime.utcnow(),
        "_index": 0,
        "semantic_scholar_id": "abc123",
    }


class TestSemanticScholarPaper:
    """Tests for SemanticScholarPaper entity."""

    def test_create_valid_paper(self, valid_paper_kwargs: dict) -> None:
        """Test creating a valid paper entity."""
        paper = SemanticScholarPaper(**valid_paper_kwargs)
        assert paper.semantic_scholar_id == "abc123"

    def test_requires_semantic_scholar_id(self, valid_paper_kwargs: dict) -> None:
        """Test that semantic_scholar_id is required."""
        valid_paper_kwargs["semantic_scholar_id"] = ""
        with pytest.raises(ValueError, match="Semantic Scholar paper ID is required"):
            SemanticScholarPaper(**valid_paper_kwargs)

    def test_optional_fields_default_to_none(self, valid_paper_kwargs: dict) -> None:
        """Test that optional fields default to None or empty list."""
        paper = SemanticScholarPaper(**valid_paper_kwargs)
        assert paper.doi is None
        assert paper.pmid is None
        assert paper.title is None
        assert paper.authors == []
        assert paper.journal is None
        assert paper.year is None
        assert paper.abstract is None
        assert paper.citation_count is None
        assert paper.influential_citation_count is None
        assert paper.fields_of_study == []
        assert paper._embedding == []

    def test_full_paper_creation(self, valid_paper_kwargs: dict) -> None:
        """Test creating a paper with all fields populated."""
        valid_paper_kwargs.update(
            {
                "doi": "10.1038/nature12373",
                "pmid": 23831764,
                "title": "Test Paper Title",
                "authors": ["John Doe", "Jane Smith"],
                "journal": "Nature",
                "year": 2023,
                "abstract": "This is the abstract.",
                "citation_count": 100,
                "influential_citation_count": 10,
                "fields_of_study": ["Computer Science", "Medicine"],
                "_embedding": [0.1, 0.2, 0.3],
            }
        )
        paper = SemanticScholarPaper(**valid_paper_kwargs)

        assert paper.doi == "10.1038/nature12373"
        assert paper.pmid == 23831764
        assert paper.title == "Test Paper Title"
        assert paper.authors == ["John Doe", "Jane Smith"]
        assert paper.journal == "Nature"
        assert paper.year == 2023
        assert paper.abstract == "This is the abstract."
        assert paper.citation_count == 100
        assert paper.influential_citation_count == 10
        assert paper.fields_of_study == ["Computer Science", "Medicine"]
        assert paper._embedding == [0.1, 0.2, 0.3]

    def test_paper_is_frozen(self, valid_paper_kwargs: dict) -> None:
        """Test that paper entity is frozen (immutable)."""
        paper = SemanticScholarPaper(**valid_paper_kwargs)
        with pytest.raises(AttributeError):
            paper.title = "New Title"  # type: ignore

    def test_requires_entity_id(self, valid_paper_kwargs: dict) -> None:
        """Test that entity_id is required (from BaseEntity)."""
        valid_paper_kwargs["entity_id"] = EntityID("")
        with pytest.raises(ValueError, match="Entity ID cannot be empty"):
            SemanticScholarPaper(**valid_paper_kwargs)

    def test_requires_content_hash(self, valid_paper_kwargs: dict) -> None:
        """Test that content_hash is required (from BaseEntity)."""
        valid_paper_kwargs["content_hash"] = ContentHash("")
        with pytest.raises(ValueError, match="Content hash cannot be empty"):
            SemanticScholarPaper(**valid_paper_kwargs)

    def test_index_cannot_be_negative(self, valid_paper_kwargs: dict) -> None:
        """Test that _index cannot be negative (from BaseEntity)."""
        valid_paper_kwargs["_index"] = -1
        with pytest.raises(ValueError, match="_index cannot be negative"):
            SemanticScholarPaper(**valid_paper_kwargs)
