# tests/unit/application/pipelines/semanticscholar/test_extractors.py
"""Unit tests for Semantic Scholar field extractors."""

from __future__ import annotations

from bioetl.application.pipelines.semanticscholar.extractors import (
    extract_authors,
    extract_external_ids,
    extract_fields_of_study,
    extract_journal_info,
    extract_open_access_info,
    extract_tldr,
    normalize_oa_status,
    validate_year,
)


class TestExtractExternalIds:
    """Tests for extract_external_ids function."""

    def test_extract_all_ids(self) -> None:
        """Test extracting all external identifier types."""
        external_ids = {
            "DOI": "10.1038/s41586-024-07487-w",
            "PubMed": "12345678",
            "PMCID": "PMC1234567",
            "ArXiv": "2106.15928",
            "CorpusId": 123456,
            "MAG": 9876543,
            "ACL": "W19-1234",
        }

        result = extract_external_ids(external_ids)

        assert result["doi"] == "10.1038/s41586-024-07487-w"
        assert result["pmid"] == "12345678"
        assert result["pmcid"] == "PMC1234567"
        assert result["arxiv"] == "2106.15928"
        assert result["corpus_id"] == 123456
        assert result["mag"] == 9876543
        assert result["acl"] == "W19-1234"

    def test_extract_partial_ids(self) -> None:
        """Test extracting when only some IDs are present."""
        external_ids = {
            "DOI": "10.1016/j.cell.2024.01.005",
            "CorpusId": 789,
        }

        result = extract_external_ids(external_ids)

        assert result["doi"] == "10.1016/j.cell.2024.01.005"
        assert result["pmid"] is None
        assert result["corpus_id"] == 789

    def test_extract_empty_dict(self) -> None:
        """Test extracting from empty dictionary."""
        result = extract_external_ids({})
        assert result == {}

    def test_extract_none(self) -> None:
        """Test extracting from None."""
        result = extract_external_ids(None)
        assert result == {}

    def test_pubmedcentral_fallback(self) -> None:
        """Test PubMedCentral as fallback for PMCID."""
        external_ids = {"PubMedCentral": "PMC7654321"}

        result = extract_external_ids(external_ids)

        assert result["pmcid"] == "PMC7654321"


class TestExtractAuthors:
    """Tests for extract_authors function."""

    def test_extract_multiple_authors(self) -> None:
        """Test extracting multiple author names."""
        authors = [
            {"authorId": "123", "name": "John Doe"},
            {"authorId": "456", "name": "Jane Smith"},
            {"authorId": "789", "name": "Bob Wilson"},
        ]

        result = extract_authors(authors)

        assert result == ["John Doe", "Jane Smith", "Bob Wilson"]

    def test_extract_single_author(self) -> None:
        """Test extracting single author."""
        authors = [{"authorId": "123", "name": "Single Author"}]

        result = extract_authors(authors)

        assert result == ["Single Author"]

    def test_skip_missing_names(self) -> None:
        """Test that authors without names are skipped."""
        authors = [
            {"authorId": "123", "name": "Has Name"},
            {"authorId": "456"},  # No name
            {"authorId": "789", "name": None},  # Explicit None
            {"authorId": "012", "name": "Also Has Name"},
        ]

        result = extract_authors(authors)

        assert result == ["Has Name", "Also Has Name"]

    def test_extract_empty_list(self) -> None:
        """Test extracting from empty list."""
        result = extract_authors([])
        assert result == []

    def test_extract_none(self) -> None:
        """Test extracting from None."""
        result = extract_authors(None)
        assert result == []


class TestExtractJournalInfo:
    """Tests for extract_journal_info function."""

    def test_extract_full_journal_info(self) -> None:
        """Test extracting complete journal information."""
        journal = {
            "name": "Nature",
            "volume": "629",
            "pages": "123-130",
        }

        result = extract_journal_info(journal, venue="Nature Publishing")

        assert result["journal_name"] == "Nature"
        assert result["volume"] == "629"
        assert result["pages"] == "123-130"

    def test_fallback_to_venue(self) -> None:
        """Test fallback to venue when journal name is missing."""
        journal = {"volume": "10"}

        result = extract_journal_info(journal, venue="Conference Proceedings")

        assert result["journal_name"] == "Conference Proceedings"
        assert result["volume"] == "10"
        assert result["pages"] is None

    def test_venue_only(self) -> None:
        """Test when only venue is provided."""
        result = extract_journal_info(None, venue="ArXiv")

        assert result["journal_name"] == "ArXiv"
        assert result["volume"] is None
        assert result["pages"] is None

    def test_empty_journal(self) -> None:
        """Test with empty journal dict."""
        result = extract_journal_info({}, venue="Fallback Venue")

        assert result["journal_name"] == "Fallback Venue"


class TestExtractOpenAccessInfo:
    """Tests for extract_open_access_info function."""

    def test_extract_open_access(self) -> None:
        """Test extracting open access information with normalized status."""
        oa_pdf = {
            "url": "https://example.com/paper.pdf",
            "status": "GREEN",
        }

        result = extract_open_access_info(True, oa_pdf)

        assert result["is_oa"] is True
        assert result["url"] == "https://example.com/paper.pdf"
        assert result["oa_status"] == "green"  # Normalized to lowercase

    def test_closed_access(self) -> None:
        """Test closed access publication gets 'closed' status."""
        result = extract_open_access_info(False, None)

        assert result["is_oa"] is False
        assert result["url"] is None
        assert result["oa_status"] == "closed"  # Now returns "closed" instead of None

    def test_none_is_open_access(self) -> None:
        """Test when is_open_access is None, defaults to closed."""
        result = extract_open_access_info(None, None)

        assert result["is_oa"] is False
        assert result["oa_status"] == "closed"

    def test_open_access_without_pdf(self) -> None:
        """Test open access without PDF info."""
        result = extract_open_access_info(True, None)

        assert result["is_oa"] is True
        assert result["url"] is None
        assert result["oa_status"] is None  # No status available

    def test_uppercase_gold_normalized(self) -> None:
        """Test that GOLD status is normalized to lowercase."""
        oa_pdf = {"url": "https://example.com/paper.pdf", "status": "GOLD"}
        result = extract_open_access_info(True, oa_pdf)
        assert result["oa_status"] == "gold"

    def test_mixed_case_hybrid_normalized(self) -> None:
        """Test that mixed case status is normalized."""
        oa_pdf = {"url": "https://example.com/paper.pdf", "status": "Hybrid"}
        result = extract_open_access_info(True, oa_pdf)
        assert result["oa_status"] == "hybrid"

    def test_unknown_status_returns_none(self) -> None:
        """Test that unknown OA status returns None."""
        oa_pdf = {"url": "https://example.com/paper.pdf", "status": "UNKNOWN"}
        result = extract_open_access_info(True, oa_pdf)
        assert result["oa_status"] is None


class TestExtractTldr:
    """Tests for extract_tldr function."""

    def test_extract_tldr(self) -> None:
        """Test extracting TLDR summary."""
        tldr = {
            "model": "tldr@v2.0.0",
            "text": "This paper presents a novel approach to...",
        }

        result = extract_tldr(tldr)

        assert result == "This paper presents a novel approach to..."

    def test_extract_none(self) -> None:
        """Test extracting from None."""
        result = extract_tldr(None)
        assert result is None

    def test_extract_empty_dict(self) -> None:
        """Test extracting from empty dict."""
        result = extract_tldr({})
        assert result is None


class TestExtractFieldsOfStudy:
    """Tests for extract_fields_of_study function."""

    def test_extract_fields(self) -> None:
        """Test extracting fields of study."""
        fields = ["Biology", "Medicine", "Genetics", "Molecular Biology"]

        result = extract_fields_of_study(fields)

        assert result == ["Biology", "Medicine", "Genetics", "Molecular Biology"]

    def test_respect_max_count(self) -> None:
        """Test max_count limit."""
        fields = ["A", "B", "C", "D", "E"]

        result = extract_fields_of_study(fields, max_count=3)

        assert result == ["A", "B", "C"]

    def test_empty_list(self) -> None:
        """Test with empty list."""
        result = extract_fields_of_study([])
        assert result == []

    def test_none(self) -> None:
        """Test with None."""
        result = extract_fields_of_study(None)
        assert result == []


class TestValidateYear:
    """Tests for validate_year function."""

    def test_valid_year(self) -> None:
        """Test valid year."""
        assert validate_year(2024) == 2024
        assert validate_year(1500) == 1500
        assert validate_year(2100) == 2100

    def test_invalid_year_too_old(self) -> None:
        """Test year before 1500."""
        assert validate_year(1499) is None

    def test_invalid_year_too_new(self) -> None:
        """Test year after 2100."""
        assert validate_year(2101) is None

    def test_none_year(self) -> None:
        """Test None year."""
        assert validate_year(None) is None


class TestNormalizeOaStatus:
    """Tests for normalize_oa_status function."""

    def test_uppercase_gold(self) -> None:
        """Test GOLD is normalized to gold."""
        assert normalize_oa_status("GOLD") == "gold"

    def test_lowercase_gold(self) -> None:
        """Test gold stays lowercase."""
        assert normalize_oa_status("gold") == "gold"

    def test_mixed_case_green(self) -> None:
        """Test Green is normalized to green."""
        assert normalize_oa_status("Green") == "green"

    def test_uppercase_hybrid(self) -> None:
        """Test HYBRID is normalized to hybrid."""
        assert normalize_oa_status("HYBRID") == "hybrid"

    def test_uppercase_bronze(self) -> None:
        """Test BRONZE is normalized to bronze."""
        assert normalize_oa_status("BRONZE") == "bronze"

    def test_closed_status(self) -> None:
        """Test closed status is valid."""
        assert normalize_oa_status("closed") == "closed"

    def test_uppercase_closed(self) -> None:
        """Test CLOSED is normalized to closed."""
        assert normalize_oa_status("CLOSED") == "closed"

    def test_unknown_returns_none(self) -> None:
        """Test unknown status returns None."""
        assert normalize_oa_status("unknown") is None

    def test_invalid_status_returns_none(self) -> None:
        """Test invalid status returns None."""
        assert normalize_oa_status("invalid") is None

    def test_empty_string_returns_none(self) -> None:
        """Test empty string returns None."""
        assert normalize_oa_status("") is None

    def test_none_returns_none(self) -> None:
        """Test None returns None."""
        assert normalize_oa_status(None) is None

    def test_whitespace_trimmed(self) -> None:
        """Test whitespace is trimmed before normalization."""
        assert normalize_oa_status("  GOLD  ") == "gold"
        assert normalize_oa_status("\tgreen\n") == "green"
