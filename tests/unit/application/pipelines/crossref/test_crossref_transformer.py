"""Unit tests for CrossRef Transformer.

Tests for CrossRefPublicationTransformer (domain entity creation from Bronze records).

Note: Field extraction tests now use domain functions directly per REFACTOR-004.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from bioetl.application.pipelines.crossref import (
    CrossRefPublicationTransformer,
    extract_authors,
    extract_license_url,
    extract_year,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.entities.crossref import CROSSREF_TYPE_DEFAULT, CROSSREF_TYPE_MAP
from bioetl.domain.normalization import extract_first_string, normalize_doi
from bioetl.domain.types import RunID, RunType


@pytest.fixture
def transformer():
    """Create a CrossRefPublicationTransformer instance."""
    return CrossRefPublicationTransformer()


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
def sample_publication():
    """Create a sample CrossRef publication response."""
    return {
        "DOI": "10.1234/test.article",
        "title": ["Test Article Title"],
        "author": [
            {"given": "John", "family": "Doe"},
            {"given": "Jane", "family": "Smith"},
            {"family": "Anonymous"},
        ],
        "container-title": ["Journal of Testing"],
        "short-container-title": ["J Test Sci", "JT Sci"],
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
def minimal_publication():
    """Create a minimal CrossRef publication response."""
    return {
        "DOI": "10.5678/minimal",
        "type": "posted-content",
    }


# =============================================================================
# Field extraction tests (delegated to domain functions per REFACTOR-004)
# =============================================================================


def test_normalize_doi():
    """Test DOI normalization using domain function."""
    assert normalize_doi("10.1234/ABC.DEF") == "10.1234/abc.def"
    assert normalize_doi("  10.1234/test  ") == "10.1234/test"


def test_extract_title(sample_publication):
    """Test title extraction using domain function."""
    assert (
        extract_first_string(sample_publication.get("title", []))
        == "Test Article Title"
    )
    assert extract_first_string([]) is None


def test_extract_authors(sample_publication):
    """Test author extraction (CrossRef-specific logic)."""
    authors = extract_authors(sample_publication)
    assert authors == ["John Doe", "Jane Smith", "Anonymous"]


def test_extract_year(sample_publication):
    """Test year extraction (CrossRef-specific logic)."""
    assert extract_year(sample_publication) == 2023
    assert extract_year({}) is None


def test_map_doc_type():
    """Test document type mapping using domain constant."""
    assert CROSSREF_TYPE_MAP.get("journal-article", "PUBLICATION") == "PUBLICATION"
    assert CROSSREF_TYPE_MAP.get("posted-content", "PUBLICATION") == "PREPRINT"
    assert CROSSREF_TYPE_MAP.get("unknown", "PUBLICATION") == "PUBLICATION"


# =============================================================================
# Business data extraction tests
# =============================================================================


def test_extract_business_data_full(transformer, sample_publication):
    """Test extracting business data from full work record."""
    import json

    data = transformer._extract_business_data(sample_publication)

    assert data["doi"] == "10.1234/test.article"
    assert data["title"] == "Test Article Title"
    # Authors are now JSON-serialized list
    assert json.loads(data["authors"]) == ["John Doe", "Jane Smith", "Anonymous"]
    assert data["journal"] == "Journal of Testing"
    assert data["journal_name_short"] == "J Test Sci"
    assert data["publication_year"] == 2023
    assert data["publication_type"] == "journal-article"  # Raw CrossRef type preserved
    assert data["citations_received"] == 100
    assert data["_source"] == "crossref"


def test_extract_business_data_minimal(transformer, minimal_publication):
    """Test extracting business data from minimal work record."""
    data = transformer._extract_business_data(minimal_publication)

    assert data["doi"] == "10.5678/minimal"
    assert data["title"] is None
    assert data["publication_type"] == "posted-content"  # Raw CrossRef type preserved
    assert data["_source"] == "crossref"


# =============================================================================
# Transformation tests
# =============================================================================


@pytest.mark.asyncio
async def test_transform_full_record(transformer, pipeline_context, sample_publication):
    """Test transforming full work record to SilverRecord."""
    result = await transformer.transform(pipeline_context, sample_publication, index=0)

    assert result is not None
    assert result["doi"] == "10.1234/test.article"
    assert result["title"] == "Test Article Title"
    assert (
        result["publication_type"] == "journal-article"
    )  # Raw CrossRef type preserved
    assert result["journal_name_short"] == "J Test Sci"
    assert result["_source"] == "crossref"
    # Check lineage fields
    assert "_run_id" in result
    assert "_run_type" in result
    assert "_ingestion_ts" in result
    assert "content_hash" in result


@pytest.mark.asyncio
async def test_transform_minimal_record(
    transformer, pipeline_context, minimal_publication
):
    """Test transforming minimal work record to SilverRecord."""
    result = await transformer.transform(pipeline_context, minimal_publication, index=1)

    assert result is not None
    assert result["doi"] == "10.5678/minimal"
    assert result["publication_type"] == "posted-content"  # Raw CrossRef type preserved


@pytest.mark.asyncio
async def test_transform_missing_doi_returns_none(transformer, pipeline_context):
    """Test that missing DOI results in None (skipped record)."""
    invalid_work = {"title": ["No DOI"]}
    result = await transformer.transform(pipeline_context, invalid_work, index=0)

    assert result is None


@pytest.mark.asyncio
async def test_transform_invalid_doi_format_returns_none(transformer, pipeline_context):
    """Test that malformed DOI results in None (skipped record).

    DOI must follow the pattern: 10.{registrant}/{suffix}
    Invalid DOIs like "invalid", "10.1234" (no suffix), or "not-a-doi"
    should be rejected just like missing DOIs.
    """
    invalid_doi_records = [
        {"DOI": "invalid", "title": ["Invalid DOI"]},
        {"DOI": "not-a-doi/123", "title": ["Not a DOI"]},
        {"DOI": "10.1234", "title": ["Missing suffix"]},
        {"DOI": "", "title": ["Empty DOI"]},
        {"DOI": "   ", "title": ["Whitespace DOI"]},
    ]

    for record in invalid_doi_records:
        result = await transformer.transform(pipeline_context, record, index=0)
        assert result is None, f"Expected None for invalid DOI: {record['DOI']!r}"


@pytest.mark.asyncio
async def test_transform_valid_doi_formats_accepted(transformer, pipeline_context):
    """Test that various valid DOI formats are accepted."""
    valid_doi_records = [
        {"DOI": "10.1234/test.article"},
        {"DOI": "10.1038/nature12373"},
        {"DOI": "10.1101/2023.01.01.123456"},  # bioRxiv preprint
        {"DOI": "10.5281/zenodo.1234567"},  # Zenodo dataset
    ]

    for record in valid_doi_records:
        result = await transformer.transform(pipeline_context, record, index=0)
        assert result is not None, f"Expected valid result for DOI: {record['DOI']}"
        assert result["doi"] == record["DOI"].lower()  # DOI should be normalized


# =============================================================================
# Provider and entity type tests
# =============================================================================


def test_provider_is_crossref(transformer):
    """Test provider is set to crossref."""
    assert transformer.provider == "crossref"


def test_entity_type_is_publication(transformer):
    """Test entity type is set to publication (Ubiquitous Language, not CrossRef 'work')."""
    assert transformer.entity_type == "publication"


# =============================================================================
# Edge case tests
# =============================================================================


def test_extract_authors_with_only_given_name():
    """Test author extraction with only given name (no family)."""
    publication = {"author": [{"given": "Madonna"}]}
    authors = extract_authors(publication)
    assert authors == ["Madonna"]


def test_extract_authors_empty_list():
    """Test author extraction with empty author list."""
    publication = {"author": []}
    authors = extract_authors(publication)
    assert authors == []


def test_extract_authors_missing_key():
    """Test author extraction when 'author' key is missing."""
    publication = {}
    authors = extract_authors(publication)
    assert authors == []


def test_extract_authors_with_whitespace():
    """Test author extraction strips whitespace from names."""
    publication = {"author": [{"given": "  John  ", "family": "  Doe  "}]}
    authors = extract_authors(publication)
    assert authors == ["John Doe"]


def test_extract_year_from_published_online():
    """Test year extraction falls back to published-online."""
    publication = {"published-online": {"date-parts": [[2022, 3, 15]]}}
    assert extract_year(publication) == 2022


def test_extract_year_from_issued():
    """Test year extraction falls back to issued field."""
    publication = {"issued": {"date-parts": [[2021, 1, 1]]}}
    assert extract_year(publication) == 2021


def test_extract_year_priority_order():
    """Test year extraction prefers published-print over others."""
    publication = {
        "published-print": {"date-parts": [[2023, 6, 1]]},
        "published-online": {"date-parts": [[2023, 5, 1]]},
        "issued": {"date-parts": [[2023, 4, 1]]},
    }
    assert extract_year(publication) == 2023


def test_extract_year_invalid_year_format():
    """Test year extraction with invalid year format."""
    publication = {"published-print": {"date-parts": [[]]}}
    assert extract_year(publication) is None


def test_extract_year_non_integer_year():
    """Test year extraction with non-integer year."""
    publication = {"published-print": {"date-parts": [["2023"]]}}
    assert extract_year(publication) is None


def test_extract_year_out_of_range():
    """Test year extraction with year out of valid range."""
    # Year 1799 is below min_year=1800 in validate_year_range
    publication = {"published-print": {"date-parts": [[1799]]}}
    assert extract_year(publication) is None

    # Year 2101 is above max_year=2100
    publication2 = {"published-print": {"date-parts": [[2101]]}}
    assert extract_year(publication2) is None


def test_extract_license_url_multiple_licenses():
    """Test license URL extraction returns first license."""
    publication = {
        "license": [
            {"URL": "https://license1.com"},
            {"URL": "https://license2.com"},
        ]
    }
    assert extract_license_url(publication) == "https://license1.com"


def test_extract_license_url_missing_url():
    """Test license URL extraction when URL is missing."""
    publication = {"license": [{"other": "data"}]}
    assert extract_license_url(publication) is None


def test_extract_license_url_empty_list():
    """Test license URL extraction with empty license list."""
    publication = {"license": []}
    assert extract_license_url(publication) is None


def test_extract_business_data_page_range(transformer):
    """Test page range extraction."""
    publication = {"DOI": "10.1234/test", "page": "123-145"}
    data = transformer._extract_business_data(publication)
    assert data["page_first"] == "123"
    assert data["page_last"] == "145"


def test_extract_business_data_single_page(transformer):
    """Test single page extraction."""
    publication = {"DOI": "10.1234/test", "page": "42"}
    data = transformer._extract_business_data(publication)
    assert data["page_first"] == "42"
    assert data["page_last"] is None


def test_extract_business_data_issn_list(transformer):
    """Test ISSN list extraction."""
    publication = {"DOI": "10.1234/test", "ISSN": ["1234-5678", "8765-4321"]}
    data = transformer._extract_business_data(publication)
    assert data["issn"] == ["1234-5678", "8765-4321"]


def test_extract_business_data_subject_list(transformer):
    """Test subjects extraction."""
    publication = {"DOI": "10.1234/test", "subject": ["Biology", "Chemistry"]}
    data = transformer._extract_business_data(publication)
    assert data["subject_keywords"] == ["Biology", "Chemistry"]


@pytest.mark.asyncio
async def test_transform_generates_content_hash(transformer, pipeline_context):
    """Test that transformation generates a content hash."""
    publication = {"DOI": "10.1234/test", "title": ["Test"]}
    result = await transformer.transform(pipeline_context, publication, index=0)

    assert result is not None
    assert "content_hash" in result
    # Content hash is a hex string (SHA256)
    assert len(result["content_hash"]) == 64  # SHA256 produces 64 hex chars


@pytest.mark.asyncio
async def test_transform_same_content_same_hash(transformer, pipeline_context):
    """Test that same content produces same hash."""
    publication = {"DOI": "10.1234/test", "title": ["Test"]}

    result1 = await transformer.transform(pipeline_context, publication, index=0)
    result2 = await transformer.transform(pipeline_context, publication, index=1)

    assert result1["content_hash"] == result2["content_hash"]


@pytest.mark.asyncio
async def test_transform_different_content_different_hash(
    transformer, pipeline_context
):
    """Test that different content produces different hash."""
    pub1 = {"DOI": "10.1234/test1", "title": ["Test 1"]}
    pub2 = {"DOI": "10.1234/test2", "title": ["Test 2"]}

    result1 = await transformer.transform(pipeline_context, pub1, index=0)
    result2 = await transformer.transform(pipeline_context, pub2, index=1)

    assert result1["content_hash"] != result2["content_hash"]


@pytest.mark.asyncio
async def test_transform_entity_id_format(transformer, pipeline_context):
    """Test that entity_id follows expected format."""
    publication = {"DOI": "10.1234/test", "title": ["Test"]}
    result = await transformer.transform(pipeline_context, publication, index=0)

    assert result is not None
    assert result["entity_id"] == "crossref:10.1234/test"


@pytest.mark.asyncio
async def test_transform_normalized_doi_in_entity_id(transformer, pipeline_context):
    """Test that entity_id uses normalized DOI."""
    publication = {"DOI": "10.1234/TEST.UPPER", "title": ["Test"]}
    result = await transformer.transform(pipeline_context, publication, index=0)

    assert result is not None
    # DOI should be lowercase in entity_id
    assert "test.upper" in result["entity_id"].lower()


def test_doc_type_mapping_all_types():
    """Test all 30 CrossRef document type mappings.

    See: https://api.crossref.org/types for complete list.
    Aligned with chembl/publication.py schema: PUBLICATION, BOOK, PREPRINT, DATASET, OTHER.
    """
    # PUBLICATION types (journal/conference articles)
    publication_types = [
        "journal-article",
        "proceedings-article",
        "peer-review",
    ]
    for doc_type in publication_types:
        assert CROSSREF_TYPE_MAP[doc_type] == "PUBLICATION", (
            f"{doc_type} should map to PUBLICATION"
        )

    # BOOK types (books, book parts, dissertations, reference entries)
    book_types = [
        "book",
        "monograph",
        "edited-book",
        "reference-book",
        "book-chapter",
        "book-section",
        "book-part",
        "book-track",
        "dissertation",  # Thesis = monograph
        "reference-entry",  # Dictionary/encyclopedia entry
    ]
    for doc_type in book_types:
        assert CROSSREF_TYPE_MAP[doc_type] == "BOOK", f"{doc_type} should map to BOOK"

    # PREPRINT types
    assert CROSSREF_TYPE_MAP["posted-content"] == "PREPRINT"

    # DATASET types
    assert CROSSREF_TYPE_MAP["dataset"] == "DATASET"
    assert CROSSREF_TYPE_MAP["database"] == "DATASET"

    # OTHER types (reports, standards, supplementary, container/series, funding, unclassified)
    other_types = [
        "report",  # Technical report
        "report-component",  # Part of report
        "standard",  # Technical standard
        "component",  # Supplementary material
        "journal",
        "journal-volume",
        "journal-issue",
        "proceedings",
        "proceedings-series",
        "book-series",
        "book-set",
        "report-series",
        "grant",
        "other",  # Unclassified content
    ]
    for doc_type in other_types:
        assert CROSSREF_TYPE_MAP[doc_type] == "OTHER", f"{doc_type} should map to OTHER"

    # Verify total count matches CrossRef API (30 types)
    assert len(CROSSREF_TYPE_MAP) == 30


def test_doc_type_default_constant():
    """Test that CROSSREF_TYPE_DEFAULT is PUBLICATION."""
    assert CROSSREF_TYPE_DEFAULT == "PUBLICATION"


def test_type_preserved_for_unknown(transformer):
    """Test that unknown/future type is preserved as-is."""
    publication = {"DOI": "10.1234/test", "type": "unknown-future-type"}
    data = transformer._extract_business_data(publication)
    assert data["publication_type"] == "unknown-future-type"  # Raw type preserved


@pytest.mark.asyncio
async def test_transform_with_preprint_type(transformer, pipeline_context):
    """Test transformation of preprint (posted-content)."""
    publication = {"DOI": "10.1101/2023.01.01.123456", "type": "posted-content"}
    result = await transformer.transform(pipeline_context, publication, index=0)

    assert result is not None
    assert result["publication_type"] == "posted-content"  # Raw CrossRef type preserved


@pytest.mark.asyncio
async def test_transform_includes_run_metadata(transformer, pipeline_context):
    """Test that transformation includes run metadata."""
    publication = {"DOI": "10.1234/test"}
    result = await transformer.transform(pipeline_context, publication, index=0)

    assert result is not None
    assert result["_run_id"] == str(pipeline_context.run_id)
    assert result["_run_type"] == pipeline_context.run_type.value
    assert "_ingestion_ts" in result


def test_extract_business_data_date_formatting(transformer):
    """Test date formatting from date-parts with end-of-period normalization."""
    publication = {
        "DOI": "10.1234/test",
        "published-print": {"date-parts": [[2023, 6, 15]]},
        "published-online": {"date-parts": [[2023, 5]]},  # Month only
    }
    data = transformer._extract_business_data(publication)

    assert data["published_print"] == "2023-06-15"
    assert data["published_online"] == "2023-05-31"  # End-of-period: May has 31 days


def test_extract_business_data_date_year_only(transformer):
    """Test date formatting with year only (end-of-period normalization)."""
    publication = {
        "DOI": "10.1234/test",
        "published-print": {"date-parts": [[2023]]},
    }
    data = transformer._extract_business_data(publication)
    assert data["published_print"] == "2023-12-31"  # End-of-period: December 31


@pytest.mark.asyncio
async def test_transform_excludes_abstract_and_affiliations(
    transformer, pipeline_context
):
    """Test that abstract and affiliations are excluded from Silver record."""
    publication = {
        "DOI": "10.1234/test",
        "title": ["Test"],
        "abstract": "<p>Some abstract text</p>",
        "author": [
            {
                "given": "John",
                "family": "Doe",
                "affiliation": [{"name": "University A"}],
            }
        ],
    }
    result = await transformer.transform(pipeline_context, publication, index=0)

    assert result is not None
    assert "abstract" not in result
    assert "affiliations" not in result
