"""Unit tests for CrossRef field extractors.

Tests for CrossRefFieldExtractor (infrastructure-level field extraction).
Domain entity creation tests are in tests/unit/application/pipelines/crossref/.
"""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.crossref.mappers import CrossRefFieldExtractor


@pytest.fixture
def mapper():
    """Create a CrossRefFieldExtractor instance."""
    return CrossRefFieldExtractor()


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
# DOI normalization tests
# =============================================================================


def test_normalize_doi_lowercase(mapper):
    """Test DOI is normalized to lowercase."""
    assert mapper.normalize_doi("10.1234/ABC.DEF") == "10.1234/abc.def"


def test_normalize_doi_strips_whitespace(mapper):
    """Test DOI normalization strips whitespace."""
    assert mapper.normalize_doi("  10.1234/test  ") == "10.1234/test"


# =============================================================================
# Title extraction tests
# =============================================================================


def test_extract_title_success(mapper, sample_work):
    """Test title extraction from work."""
    assert mapper.extract_title(sample_work) == "Test Article Title"


def test_extract_title_empty_list(mapper):
    """Test title extraction with empty list."""
    assert mapper.extract_title({"title": []}) is None


def test_extract_title_missing(mapper):
    """Test title extraction when field is missing."""
    assert mapper.extract_title({}) is None


# =============================================================================
# Author extraction tests
# =============================================================================


def test_extract_authors_full_names(mapper, sample_work):
    """Test author extraction with full names."""
    authors = mapper.extract_authors(sample_work)
    assert authors == ["John Doe", "Jane Smith", "Anonymous"]


def test_extract_authors_only_family(mapper):
    """Test author extraction with only family name."""
    work = {"author": [{"family": "Smith"}]}
    assert mapper.extract_authors(work) == ["Smith"]


def test_extract_authors_only_given(mapper):
    """Test author extraction with only given name."""
    work = {"author": [{"given": "John"}]}
    assert mapper.extract_authors(work) == ["John"]


def test_extract_authors_empty(mapper):
    """Test author extraction with no authors."""
    assert mapper.extract_authors({}) == []


# =============================================================================
# Journal extraction tests
# =============================================================================


def test_extract_journal_success(mapper, sample_work):
    """Test journal extraction."""
    assert mapper.extract_journal(sample_work) == "Journal of Testing"


def test_extract_journal_empty(mapper):
    """Test journal extraction with empty container-title."""
    assert mapper.extract_journal({"container-title": []}) is None


def test_extract_journal_missing(mapper):
    """Test journal extraction when field is missing."""
    assert mapper.extract_journal({}) is None


# =============================================================================
# Year extraction tests
# =============================================================================


def test_extract_year_from_published_print(mapper, sample_work):
    """Test year extraction from published-print."""
    assert mapper.extract_year(sample_work) == 2023


def test_extract_year_from_published_online(mapper):
    """Test year extraction falls back to published-online."""
    work = {"published-online": {"date-parts": [[2022, 3, 1]]}}
    assert mapper.extract_year(work) == 2022


def test_extract_year_from_issued(mapper):
    """Test year extraction falls back to issued."""
    work = {"issued": {"date-parts": [[2021]]}}
    assert mapper.extract_year(work) == 2021


def test_extract_year_missing(mapper):
    """Test year extraction when no date fields present."""
    assert mapper.extract_year({}) is None


def test_extract_year_invalid(mapper):
    """Test year extraction with invalid year."""
    work = {"published-print": {"date-parts": [[1500]]}}
    assert mapper.extract_year(work) is None


# =============================================================================
# Date formatting tests
# =============================================================================


def test_format_date_parts_full(mapper):
    """Test formatting complete date."""
    result = mapper.format_date_parts([[2023, 6, 15]])
    assert result == "2023-06-15"


def test_format_date_parts_year_month(mapper):
    """Test formatting year-month date."""
    result = mapper.format_date_parts([[2023, 6]])
    assert result == "2023-06"


def test_format_date_parts_year_only(mapper):
    """Test formatting year-only date."""
    result = mapper.format_date_parts([[2023]])
    assert result == "2023"


def test_format_date_parts_empty(mapper):
    """Test formatting empty date parts."""
    assert mapper.format_date_parts(None) is None
    assert mapper.format_date_parts([]) is None
    assert mapper.format_date_parts([[]]) is None


# =============================================================================
# Page extraction tests
# =============================================================================


def test_extract_pages_range(mapper, sample_work):
    """Test page extraction with range."""
    first, last = mapper.extract_pages(sample_work)
    assert first == "123"
    assert last == "145"


def test_extract_pages_single(mapper):
    """Test page extraction with single page."""
    first, last = mapper.extract_pages({"page": "42"})
    assert first == "42"
    assert last is None


def test_extract_pages_empty(mapper):
    """Test page extraction with no page field."""
    first, last = mapper.extract_pages({})
    assert first is None
    assert last is None


# =============================================================================
# Abstract extraction tests
# =============================================================================


def test_extract_abstract_strips_html(mapper, sample_work):
    """Test abstract extraction strips HTML tags."""
    result = mapper.extract_abstract(sample_work)
    assert result == "This is the abstract text."


def test_extract_abstract_empty(mapper):
    """Test abstract extraction with empty abstract."""
    assert mapper.extract_abstract({"abstract": ""}) is None


def test_extract_abstract_missing(mapper):
    """Test abstract extraction when field is missing."""
    assert mapper.extract_abstract({}) is None


def test_strip_html_tags(mapper):
    """Test HTML tag stripping."""
    text = "<p>Hello <strong>World</strong>!</p>"
    assert mapper.strip_html_tags(text) == "Hello World!"


# =============================================================================
# Document type mapping tests
# =============================================================================


def test_map_doc_type_journal_article(mapper):
    """Test mapping journal-article to PUBLICATION."""
    assert mapper.map_doc_type("journal-article") == "PUBLICATION"


def test_map_doc_type_preprint(mapper):
    """Test mapping posted-content to PREPRINT."""
    assert mapper.map_doc_type("posted-content") == "PREPRINT"


def test_map_doc_type_unknown(mapper):
    """Test mapping unknown type defaults to PUBLICATION."""
    assert mapper.map_doc_type("unknown-type") == "PUBLICATION"


# =============================================================================
# ISSN extraction tests
# =============================================================================


def test_extract_issn_list(mapper, sample_work):
    """Test ISSN extraction."""
    issns = mapper.extract_issn(sample_work)
    assert issns == ["1234-5678", "8765-4321"]


def test_extract_issn_empty(mapper):
    """Test ISSN extraction with no ISSNs."""
    assert mapper.extract_issn({}) == []


# =============================================================================
# License extraction tests
# =============================================================================


def test_extract_license_url(mapper, sample_work):
    """Test license URL extraction."""
    result = mapper.extract_license_url(sample_work)
    assert result == "https://creativecommons.org/licenses/by/4.0/"


def test_extract_license_url_empty(mapper):
    """Test license URL extraction with no licenses."""
    assert mapper.extract_license_url({}) is None


# =============================================================================
# Subjects extraction tests
# =============================================================================


def test_extract_subjects(mapper, sample_work):
    """Test subjects extraction."""
    subjects = mapper.extract_subjects(sample_work)
    assert subjects == ["Computer Science", "Information Systems"]


def test_extract_subjects_empty(mapper):
    """Test subjects extraction with no subjects."""
    assert mapper.extract_subjects({}) == []


# =============================================================================
# map_to_dict tests
# =============================================================================


def test_map_to_dict(mapper, sample_work):
    """Test mapping work to dictionary for Bronze storage."""
    result = mapper.map_to_dict(sample_work)

    assert result["doi"] == "10.1234/test.article"
    assert result["title"] == "Test Article Title"
    assert result["authors"] == ["John Doe", "Jane Smith", "Anonymous"]
    assert result["journal"] == "Journal of Testing"
    assert result["year"] == 2023
    assert result["doc_type"] == "PUBLICATION"
    assert result["source"] == "crossref"
    assert result["_raw_type"] == "journal-article"
