"""Unit tests for OpenAlex field extractors.

Tests the pure functions in extractors.py module.
"""

from __future__ import annotations

from bioetl.application.pipelines.openalex.extractors import (
    extract_authors,
    extract_concepts,
    extract_doi,
    extract_journal_info,
    extract_open_access_info,
    extract_openalex_id,
    reconstruct_abstract,
)


class TestExtractDoi:
    """Tests for extract_doi function."""

    def test_extract_doi_from_full_url(self) -> None:
        """Should extract DOI from https://doi.org/ URL."""
        result = extract_doi("https://doi.org/10.1038/s41586-024-07487-w")
        assert result == "10.1038/s41586-024-07487-w"

    def test_extract_doi_from_http_url(self) -> None:
        """Should extract DOI from http://doi.org/ URL."""
        result = extract_doi("http://doi.org/10.1016/j.cell.2024.01.005")
        assert result == "10.1016/j.cell.2024.01.005"

    def test_extract_doi_from_doi_prefix(self) -> None:
        """Should extract DOI from doi: prefix."""
        result = extract_doi("doi:10.1126/science.abc1234")
        assert result == "10.1126/science.abc1234"

    def test_extract_doi_bare_doi(self) -> None:
        """Should return bare DOI unchanged."""
        result = extract_doi("10.1001/jama.2024.0001")
        assert result == "10.1001/jama.2024.0001"

    def test_extract_doi_none(self) -> None:
        """Should return None for None input."""
        result = extract_doi(None)
        assert result is None

    def test_extract_doi_empty_string(self) -> None:
        """Should return None for empty input."""
        result = extract_doi("")
        assert result is None


class TestExtractOpenalexId:
    """Tests for extract_openalex_id function."""

    def test_extract_id_from_full_url(self) -> None:
        """Should extract ID from full OpenAlex URL."""
        result = extract_openalex_id("https://openalex.org/W2148763428")
        assert result == "W2148763428"

    def test_extract_id_bare_id(self) -> None:
        """Should return bare ID unchanged."""
        result = extract_openalex_id("W2148763428")
        assert result == "W2148763428"

    def test_extract_id_none(self) -> None:
        """Should return None for None input."""
        result = extract_openalex_id(None)
        assert result is None


class TestExtractAuthors:
    """Tests for extract_authors function."""

    def test_extract_authors_with_display_names(self) -> None:
        """Should extract author display names from authorships."""
        authorships = [
            {"author": {"display_name": "John Doe", "id": "A123"}},
            {"author": {"display_name": "Jane Smith", "id": "A456"}},
        ]
        result = extract_authors(authorships)
        assert result == ["John Doe", "Jane Smith"]

    def test_extract_authors_empty_list(self) -> None:
        """Should return empty list for empty authorships."""
        result = extract_authors([])
        assert result == []

    def test_extract_authors_missing_display_name(self) -> None:
        """Should skip authorships without display_name."""
        authorships = [
            {"author": {"id": "A123"}},  # No display_name
            {"author": {"display_name": "Jane Smith"}},
        ]
        result = extract_authors(authorships)
        assert result == ["Jane Smith"]

    def test_extract_authors_with_whitespace(self) -> None:
        """Should strip whitespace from author names."""
        authorships = [
            {"author": {"display_name": "  John Doe  "}},
        ]
        result = extract_authors(authorships)
        assert result == ["John Doe"]

    def test_extract_authors_invalid_structure(self) -> None:
        """Should handle invalid authorship structure gracefully."""
        authorships = [
            {"author": None},  # Invalid author
            {"not_author": {}},  # Missing author key
            {"author": "string"},  # Invalid type
        ]
        result = extract_authors(authorships)
        assert result == []


class TestExtractConcepts:
    """Tests for extract_concepts function."""

    def test_extract_concepts_basic(self) -> None:
        """Should extract concept display names."""
        concepts = [
            {"display_name": "Chemistry", "score": 0.9},
            {"display_name": "Biology", "score": 0.7},
        ]
        result = extract_concepts(concepts)
        assert result == ["Chemistry", "Biology"]

    def test_extract_concepts_with_limit(self) -> None:
        """Should respect max_count limit."""
        concepts = [
            {"display_name": f"Concept{i}", "score": 0.9 - i * 0.1} for i in range(20)
        ]
        result = extract_concepts(concepts, max_count=5)
        assert len(result) == 5
        assert result[0] == "Concept0"

    def test_extract_concepts_empty(self) -> None:
        """Should return empty list for empty concepts."""
        result = extract_concepts([])
        assert result == []

    def test_extract_concepts_strips_whitespace(self) -> None:
        """Should strip whitespace from concept names."""
        concepts = [{"display_name": "  Chemistry  "}]
        result = extract_concepts(concepts)
        assert result == ["Chemistry"]


class TestExtractJournalInfo:
    """Tests for extract_journal_info function."""

    def test_extract_journal_info_complete(self) -> None:
        """Should extract all journal fields."""
        primary_location = {
            "source": {
                "display_name": "Nature",
                "issn_l": "0028-0836",
                "host_organization_name": "Springer Nature",
            }
        }
        result = extract_journal_info(primary_location)
        assert result == {
            "journal_name": "Nature",
            "issn": "0028-0836",
            "publisher": "Springer Nature",
        }

    def test_extract_journal_info_partial(self) -> None:
        """Should handle missing fields gracefully."""
        primary_location = {
            "source": {
                "display_name": "Nature",
            }
        }
        result = extract_journal_info(primary_location)
        assert result["journal_name"] == "Nature"
        assert result["issn"] is None
        assert result["publisher"] is None

    def test_extract_journal_info_none(self) -> None:
        """Should return None values for None input."""
        result = extract_journal_info(None)
        assert result == {"journal_name": None, "issn": None, "publisher": None}

    def test_extract_journal_info_empty_source(self) -> None:
        """Should handle empty source gracefully."""
        result = extract_journal_info({"source": None})
        assert result == {"journal_name": None, "issn": None, "publisher": None}


class TestReconstructAbstract:
    """Tests for reconstruct_abstract function."""

    def test_reconstruct_abstract_basic(self) -> None:
        """Should reconstruct abstract from inverted index."""
        inverted_index = {
            "This": [0],
            "is": [1],
            "a": [2],
            "test": [3],
        }
        result = reconstruct_abstract(inverted_index)
        assert result == "This is a test"

    def test_reconstruct_abstract_with_repeated_words(self) -> None:
        """Should handle words appearing multiple times."""
        inverted_index = {
            "The": [0],
            "test": [1, 4],
            "is": [2, 5],
            "a": [3],
            "good": [6],
        }
        result = reconstruct_abstract(inverted_index)
        assert result == "The test is a test is good"

    def test_reconstruct_abstract_none(self) -> None:
        """Should return None for None input."""
        result = reconstruct_abstract(None)
        assert result is None

    def test_reconstruct_abstract_empty(self) -> None:
        """Should return None for empty dict."""
        result = reconstruct_abstract({})
        assert result is None

    def test_reconstruct_abstract_invalid_positions(self) -> None:
        """Should skip invalid position values."""
        inverted_index = {
            "Valid": [0, 1],
            "invalid": ["not_int"],  # Invalid position
        }
        result = reconstruct_abstract(inverted_index)
        assert result == "Valid Valid"


class TestExtractOpenAccessInfo:
    """Tests for extract_open_access_info function."""

    def test_extract_oa_info_gold(self) -> None:
        """Should extract OA info for gold status."""
        oa = {"is_oa": True, "oa_status": "gold"}
        result = extract_open_access_info(oa)
        assert result == {"is_oa": True, "oa_status": "gold"}

    def test_extract_oa_info_closed(self) -> None:
        """Should extract OA info for closed status."""
        oa = {"is_oa": False, "oa_status": "closed"}
        result = extract_open_access_info(oa)
        assert result == {"is_oa": False, "oa_status": "closed"}

    def test_extract_oa_info_none(self) -> None:
        """Should return None values for None input."""
        result = extract_open_access_info(None)
        assert result == {"is_oa": None, "oa_status": None}

    def test_extract_oa_info_empty(self) -> None:
        """Should return None values for empty dict."""
        result = extract_open_access_info({})
        assert result == {"is_oa": None, "oa_status": None}
