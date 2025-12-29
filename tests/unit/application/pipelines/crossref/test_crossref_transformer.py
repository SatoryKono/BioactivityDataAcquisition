"""Unit tests for CrossRef Transformer.

Tests for CrossRefTransformer (domain entity creation from Bronze records).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from bioetl.application.pipelines.crossref.transformer import CrossRefTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunID, RunType


@pytest.fixture
def transformer():
    """Create a CrossRefTransformer instance."""
    return CrossRefTransformer()


@pytest.fixture
def pipeline_context(noop_logger):
    """Create a minimal PipelineContext for testing."""
    return PipelineContext.create(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        logger=noop_logger,
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_work():
    """Create a sample CrossRef work response."""
    return {
        "DOI": "10.1234/test.article",
        "title": ["Test Article Title"],
        "abstract": "<p>This is the <b>abstract</b> text.</p>",
        "author": [
            {"given": "John", "family": "Doe"},
            {"given": "Jane", "family": "Smith"},
            {"family": "Anonymous"},
        ],
        "container-title": ["Journal of Testing"],
        "ISSN": ["1234-5678", "8765-4321"],
        "publisher": "Test Publisher Inc.",
        "volume": "42",
        "issue": "3",
        "page": "123-145",
        "published-print": {"date-parts": [[2023, 6, 15]]},
        "published-online": {"date-parts": [[2023, 5, 1]]},
        "type": "journal-article",
        "is-referenced-by-count": 100,
        "references-count": 50,
        "language": "en",
        "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
        "subject": ["Computer Science", "Information Systems"],
    }


@pytest.fixture
def minimal_work():
    """Create a minimal CrossRef work response."""
    return {
        "DOI": "10.5678/minimal",
        "type": "posted-content",
    }


# =============================================================================
# Field extraction tests (delegated to static methods)
# =============================================================================


def test_normalize_doi(transformer):
    """Test DOI normalization."""
    assert transformer.normalize_doi("10.1234/ABC.DEF") == "10.1234/abc.def"
    assert transformer.normalize_doi("  10.1234/test  ") == "10.1234/test"


def test_extract_title(transformer, sample_work):
    """Test title extraction."""
    assert transformer.extract_title(sample_work) == "Test Article Title"
    assert transformer.extract_title({}) is None


def test_extract_authors(transformer, sample_work):
    """Test author extraction."""
    authors = transformer.extract_authors(sample_work)
    assert authors == ["John Doe", "Jane Smith", "Anonymous"]


def test_extract_year(transformer, sample_work):
    """Test year extraction."""
    assert transformer.extract_year(sample_work) == 2023
    assert transformer.extract_year({}) is None


def test_map_doc_type(transformer):
    """Test document type mapping."""
    assert transformer.map_doc_type("journal-article") == "PUBLICATION"
    assert transformer.map_doc_type("posted-content") == "PREPRINT"
    assert transformer.map_doc_type("unknown") == "PUBLICATION"


# =============================================================================
# Business data extraction tests
# =============================================================================


def test_extract_business_data_full(transformer, sample_work):
    """Test extracting business data from full work record."""
    data = transformer._extract_business_data(sample_work)

    assert data["doi"] == "10.1234/test.article"
    assert data["title"] == "Test Article Title"
    assert data["abstract"] == "This is the abstract text."
    assert data["authors"] == ["John Doe", "Jane Smith", "Anonymous"]
    assert data["journal"] == "Journal of Testing"
    assert data["year"] == 2023
    assert data["doc_type"] == "PUBLICATION"
    assert data["citation_count"] == 100
    assert data["source"] == "crossref"


def test_extract_business_data_minimal(transformer, minimal_work):
    """Test extracting business data from minimal work record."""
    data = transformer._extract_business_data(minimal_work)

    assert data["doi"] == "10.5678/minimal"
    assert data["title"] is None
    assert data["doc_type"] == "PREPRINT"
    assert data["source"] == "crossref"


# =============================================================================
# Transformation tests
# =============================================================================


@pytest.mark.asyncio
async def test_transform_full_record(transformer, pipeline_context, sample_work):
    """Test transforming full work record to SilverRecord."""
    result = await transformer.transform(pipeline_context, sample_work, index=0)

    assert result is not None
    assert result["doi"] == "10.1234/test.article"
    assert result["title"] == "Test Article Title"
    assert result["doc_type"] == "PUBLICATION"
    assert result["source"] == "crossref"
    # Check lineage fields
    assert "_run_id" in result
    assert "_run_type" in result
    assert "_ingestion_ts" in result
    assert "content_hash" in result


@pytest.mark.asyncio
async def test_transform_minimal_record(transformer, pipeline_context, minimal_work):
    """Test transforming minimal work record to SilverRecord."""
    result = await transformer.transform(pipeline_context, minimal_work, index=1)

    assert result is not None
    assert result["doi"] == "10.5678/minimal"
    assert result["doc_type"] == "PREPRINT"


@pytest.mark.asyncio
async def test_transform_missing_doi_returns_none(transformer, pipeline_context):
    """Test that missing DOI results in None (skipped record)."""
    invalid_work = {"title": ["No DOI"]}
    result = await transformer.transform(pipeline_context, invalid_work, index=0)

    assert result is None


# =============================================================================
# Provider and entity type tests
# =============================================================================


def test_provider_is_crossref(transformer):
    """Test provider is set to crossref."""
    assert transformer.provider == "crossref"


def test_entity_type_is_work(transformer):
    """Test entity type is set to work."""
    assert transformer.entity_type == "work"
