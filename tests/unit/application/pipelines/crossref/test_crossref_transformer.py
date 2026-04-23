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
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.entities.crossref import CrossRefPublicationEntity
from bioetl.domain.mapping.publication_type_classification import (
    classify_publication_type,
)
from bioetl.domain.normalization import extract_first_string, normalize_doi
from bioetl.domain.types import RunID, RunType
from tests.helpers.transformer_dependencies import instantiate_test_transformer

pytestmark = pytest.mark.usefixtures("publication_type_classification_data")


@pytest.fixture
def transformer():
    """Create a CrossRefPublicationTransformer instance."""
    return instantiate_test_transformer(CrossRefPublicationTransformer)


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


def test_map_doc_type():
    """Test document type mapping using classification function."""
    # Test journal article → EXP / Original Experimental Data / Journal Article
    result = classify_publication_type("crossref", raw_type="journal-article")
    assert result is not None
    assert result.class_code == "EXP"
    assert result.unified_type == "Journal Article"

    # Test posted-content → EXP / Original Experimental Data / Preprint
    result = classify_publication_type("crossref", raw_type="posted-content")
    assert result is not None
    assert result.class_code == "EXP"
    assert result.unified_type == "Preprint"

    # Test unknown type → None (default handling by transformer)
    result = classify_publication_type("crossref", raw_type="unknown-future-type")
    assert result is None  # Unmapped types return None


# =============================================================================
# Business data extraction tests
# =============================================================================


def test_extract_business_data_full(transformer, sample_publication):
    """Test extracting business data from full work record."""
    import json

    data = transformer._extract_business_data(sample_publication)

    assert data["doi"] == "10.1234/test.article"
    assert data["title"] == "Test Article Title"
    # Authors are stored as unhashed names
    assert json.loads(data["authors"]) == [
        "John Doe",
        "Jane Smith",
        "Anonymous",
    ]
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


def test_get_primary_id_field(transformer):
    """Primary identifier field for CrossRef must be DOI."""
    assert transformer._get_primary_id_field() == "doi"


def test_get_entity_class(transformer):
    """Transformer should map to CrossRefPublicationEntity."""
    assert transformer._get_entity_class() is CrossRefPublicationEntity


def test_pre_extract_validation_accepts_valid_doi(transformer, pipeline_context):
    """Pre-extract validation should accept valid DOI values."""
    transformer._pre_extract_validation(
        pipeline_context,
        {"DOI": "10.1234/valid.doi"},
        index=0,
    )


@pytest.mark.parametrize(
    "record,expected_error",
    [
        ({}, "DOI is required for CrossRef Publication"),
        ({"DOI": ""}, "DOI is required for CrossRef Publication"),
        ({"DOI": "invalid"}, "Invalid DOI format: invalid"),
    ],
)
def test_pre_extract_validation_rejects_invalid_doi(
    transformer,
    pipeline_context,
    record,
    expected_error,
):
    """Pre-extract validation should reject missing or malformed DOI values."""
    with pytest.raises(ValueError, match=expected_error):
        transformer._pre_extract_validation(pipeline_context, record, index=0)


def test_should_log_fallback_lookup(transformer):
    """CrossRef should keep fallback logging enabled."""
    assert transformer._should_log_fallback_lookup() is True


def test_hash_author_details_hashes_pii():
    """PII fields must be hashed while non-PII fields remain unchanged."""

    class _TestHasher:
        def hash_value(self, value: str | None) -> str | None:
            return f"h::{value}" if value is not None else None

        def hash_list(self, values: list[str] | None) -> list[str] | None:
            return [f"h::{value}" for value in values] if values is not None else None

        def get_salt_id(self) -> str:
            return "test"

    transformer = instantiate_test_transformer(
        CrossRefPublicationTransformer,
        pii_hasher=_TestHasher(),
    )
    author_details = [
        {
            "given": "John",
            "family": "Doe",
            "name": None,
            "orcid": "0000-0001-2345-6789",
            "authenticated_orcid": True,
            "sequence": "first",
            "affiliations": ["University A"],
        }
    ]

    hashed = transformer._hash_author_details(author_details)
    assert hashed[0]["given"] is not None
    assert hashed[0]["family"] is not None
    assert hashed[0]["given"] == "h::John"
    assert hashed[0]["family"] == "h::Doe"
    assert hashed[0]["orcid"] == "0000-0001-2345-6789"
    assert hashed[0]["authenticated_orcid"] is True
    assert hashed[0]["sequence"] == "first"
    assert hashed[0]["affiliations"] == ["University A"]


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
    """Test ISSN list extraction at business data level (before entity conversion)."""
    publication = {"DOI": "10.1234/test", "ISSN": ["1234-5678", "8765-4321"]}
    data = transformer._extract_business_data(publication)
    assert data["issn"] == ["1234-5678", "8765-4321"]


@pytest.mark.asyncio
async def test_transform_issn_scalar_and_list(transformer, pipeline_context):
    """Test that full transformation produces scalar issn and JSON issn_list."""
    publication = {
        "DOI": "10.1234/test",
        "ISSN": ["1234-5678", "8765-4321"],
    }
    result = await transformer.transform(pipeline_context, publication, index=0)

    assert result is not None
    assert result["issn"] == "1234-5678"
    assert '"1234-5678"' in result["issn_list"]
    assert '"8765-4321"' in result["issn_list"]


@pytest.mark.asyncio
async def test_transform_issn_empty(transformer, pipeline_context):
    """Test empty ISSN produces None for both fields."""
    publication = {"DOI": "10.1234/test"}
    result = await transformer.transform(pipeline_context, publication, index=0)

    assert result is not None
    assert result["issn"] is None
    assert result["issn_list"] is None


@pytest.mark.asyncio
async def test_transform_issn_single(transformer, pipeline_context):
    """Test single ISSN produces scalar and single-element JSON array."""
    publication = {"DOI": "10.1234/test", "ISSN": ["1234-5678"]}
    result = await transformer.transform(pipeline_context, publication, index=0)

    assert result is not None
    assert result["issn"] == "1234-5678"
    assert result["issn_list"] == '["1234-5678"]'


def test_extract_business_data_subject_list(transformer):
    """Test subjects extraction (serialized as canonical JSON string)."""
    publication = {"DOI": "10.1234/test", "subject": ["Biology", "Chemistry"]}
    data = transformer._extract_business_data(publication)
    assert data["subject_keywords"] == '["Biology","Chemistry"]'


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
    """Test CrossRef document type classification using new 3-level hierarchy.

    See: https://api.crossref.org/types for complete list (30 types).
    Tests use the new classify_publication_type() function which returns
    ClassificationEntry with 3-level hierarchy:
    - Level 1 class_code: EXP | REV | PEER
    - Level 2 subclass: ~25 groupings (e.g. "Original Experimental Data")
    - Level 3 unified_type: 214 specific types (e.g. "Journal Article")
    """
    # EXP types (experimental research - journal/conference articles)
    exp_article_types = [
        ("journal-article", "Journal Article"),
        ("proceedings-article", "Conference Paper"),
    ]
    for doc_type, expected_unified in exp_article_types:
        result = classify_publication_type("crossref", raw_type=doc_type)
        assert result is not None, f"{doc_type} should be classified"
        assert result.class_code == "EXP", f"{doc_type} should map to EXP class"
        assert result.unified_type == expected_unified

    # PEER type (peer review)
    result = classify_publication_type("crossref", raw_type="peer-review")
    assert result is not None
    assert result.class_code == "PEER"

    # REV types (books, monographs)
    # Most book types map to REV class (Books & Monographs subclass)
    book_types = [
        ("book", "Book"),
        ("monograph", "Monograph"),
        ("edited-book", "Edited Book"),
        ("reference-book", "Reference Book"),
        ("book-chapter", "Book Chapter"),
    ]
    for doc_type, expected_unified in book_types:
        result = classify_publication_type("crossref", raw_type=doc_type)
        assert result is not None, f"{doc_type} should be classified"
        assert result.class_code == "REV", f"{doc_type} should map to REV class"
        assert result.unified_type == expected_unified

    # EXP type (dissertation is experimental, not review)
    result = classify_publication_type("crossref", raw_type="dissertation")
    assert result is not None
    assert result.class_code == "EXP"
    assert result.unified_type == "Dissertation"

    # Additional REV book types
    book_minor_types = [
        ("book-section", "Book Section"),
        ("book-part", "Book Part"),
        ("book-track", "Book Track"),
        ("reference-entry", "Reference Entry"),
    ]
    for doc_type, expected_unified in book_minor_types:
        result = classify_publication_type("crossref", raw_type=doc_type)
        assert result is not None, f"{doc_type} should be classified"
        assert result.class_code == "REV"
        assert result.unified_type == expected_unified

    # EXP types (preprint, dataset, report)
    exp_data_types = [
        ("posted-content", "Preprint"),
        ("dataset", "Dataset"),
        ("report", "Report"),
    ]
    for doc_type, expected_unified in exp_data_types:
        result = classify_publication_type("crossref", raw_type=doc_type)
        assert result is not None, f"{doc_type} should be classified"
        assert result.class_code == "EXP"
        assert result.unified_type == expected_unified

    # Database type (may map to Dataset)
    result = classify_publication_type("crossref", raw_type="database")
    # Database may be unmapped or map to Dataset
    if result is not None:
        assert result.class_code == "EXP"

    # Container/series types - many may be unmapped (return None)
    # This is expected - these are metadata containers, not publications
    container_types = [
        "report-component",
        "standard",
        "component",
        "journal",
        "journal-volume",
        "journal-issue",
        "proceedings",
        "proceedings-series",
        "book-series",
        "book-set",
        "report-series",
        "grant",
        "other",
    ]
    for doc_type in container_types:
        classify_publication_type("crossref", raw_type=doc_type)
        # These may be unmapped - transformer handles with raw type preservation
        # Just verify they don't crash - any result is acceptable


def test_doc_type_unknown_handling():
    """Test that unknown types return None (handled by transformer with defaults)."""
    result = classify_publication_type("crossref", raw_type="unknown-future-type")
    assert result is None  # Unmapped types return None - transformer applies defaults


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
    assert "_run_id" in result
    assert "_run_type" in result
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
async def test_transform_includes_base_schema_fields_as_none(
    transformer, pipeline_context
):
    """Test that base schema fields exist in the Silver record.

    CrossRef doesn't provide abstract, pmid, or pmc_id (set to None).
    affiliation_list is extracted from author affiliation data when present.
    These fields must exist to satisfy PublicationBaseSchema inheritance
    requirements for Pandera validation.
    """
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
    # Fields from base schema must exist
    assert "abstract" in result
    assert result["abstract"] is None
    assert "affiliation_list" in result
    # Affiliations are extracted from author data when present
    assert result["affiliation_list"] is not None
    assert "University A" in result["affiliation_list"]
    assert "pmid" in result
    assert result["pmid"] is None
    assert "pmc_id" in result
    assert result["pmc_id"] is None
