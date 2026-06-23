# tests/unit/application/pipelines/semanticscholar/test_extractors.py
"""Unit tests for Semantic Scholar field extractors."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from bioetl.application.pipelines.semanticscholar.extractors import (
    extract_affiliations,
    extract_author_h_indices,
    extract_author_orcids,
    extract_author_s2_ids,
    extract_authors,
    extract_citation_contexts,
    extract_external_ids,
    extract_fields_of_study,
    extract_journal_info,
    extract_open_access_info,
    extract_tldr,
    normalize_oa_status,
    parse_page_range,
    parse_volume_issue,
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
        assert result["pmmolecule_id"] == "PMC1234567"
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

        assert result["pmmolecule_id"] == "PMC7654321"

    def test_extract_dblp_id(self) -> None:
        """Test DBLP ID extraction."""
        external_ids = {
            "DOI": "10.1145/12345",
            "DBLP": "journals/cacm/Smith24",
        }

        result = extract_external_ids(external_ids)

        assert result["dblp"] == "journals/cacm/Smith24"
        assert result["doi"] == "10.1145/12345"

    def test_extract_all_ids_including_dblp(self) -> None:
        """Test extracting all identifier types including DBLP."""
        external_ids = {
            "DOI": "10.1038/s41586-024-07487-w",
            "PubMed": "12345678",
            "PMCID": "PMC1234567",
            "ArXiv": "2106.15928",
            "CorpusId": 123456,
            "MAG": 9876543,
            "DBLP": "conf/icml/AuthorYear",
            "ACL": "W19-1234",
        }

        result = extract_external_ids(external_ids)

        assert result["doi"] == "10.1038/s41586-024-07487-w"
        assert result["pmid"] == "12345678"
        assert result["pmmolecule_id"] == "PMC1234567"
        assert result["arxiv"] == "2106.15928"
        assert result["corpus_id"] == 123456
        assert result["mag"] == 9876543
        assert result["dblp"] == "conf/icml/AuthorYear"
        assert result["acl"] == "W19-1234"


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

    def test_extract_authors__single_author__a9841583(self) -> None:
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

    def test_extract_authors__extract_none__a0d49a5a(self) -> None:
        """Test extracting from None."""
        result = extract_authors(None)
        assert result == []

    def test_skip_whitespace_only_names(self) -> None:
        """Test that whitespace-only names are skipped."""
        authors = [
            {"authorId": "123", "name": "Valid Name"},
            {"authorId": "456", "name": "   "},  # Whitespace only
            {"authorId": "789", "name": "\t\n"},  # Tabs and newlines
            {"authorId": "012", "name": "Another Valid"},
        ]

        result = extract_authors(authors)

        assert result == ["Valid Name", "Another Valid"]

    def test_skip_empty_string_names(self) -> None:
        """Test that empty string names are skipped."""
        authors = [
            {"authorId": "123", "name": "Valid"},
            {"authorId": "456", "name": ""},  # Empty string
            {"authorId": "789", "name": "Also Valid"},
        ]

        result = extract_authors(authors)

        assert result == ["Valid", "Also Valid"]

    def test_names_are_stripped(self) -> None:
        """Test that author names are stripped of whitespace."""
        authors = [
            {"authorId": "123", "name": "  John Doe  "},
            {"authorId": "456", "name": "\tJane Smith\n"},
        ]

        result = extract_authors(authors)

        assert result == ["John Doe", "Jane Smith"]


class TestExtractAffiliations:
    """Tests for extract_affiliations function."""

    def test_extract_affiliations_strings(self) -> None:
        """Should extract affiliations from list of strings."""
        authors = [
            {"name": "John", "affiliations": ["Univ A"]},
            {"name": "Jane", "affiliations": ["Univ B", "Univ A"]},
        ]
        result = extract_affiliations(authors)
        assert result == ["Univ A", "Univ B"]

    def test_extract_affiliations_empty_list(self) -> None:
        """Should handle empty affiliation lists."""
        authors = [
            {"name": "John", "affiliations": []},
            {"name": "Jane", "affiliations": ["Univ A"]},
        ]
        result = extract_affiliations(authors)
        assert result == ["Univ A"]

    def test_extract_affiliations_none(self) -> None:
        """Should handle None affiliations."""
        authors = [
            {"name": "John", "affiliations": None},
            {"name": "Jane", "affiliations": ["Univ A"]},
        ]
        result = extract_affiliations(authors)
        assert result == ["Univ A"]

    def test_extract_affiliations__deduplication__4e55f83b(self) -> None:
        """Should deduplicate affiliations."""
        authors = [
            {"name": "John", "affiliations": ["Univ A"]},
            {"name": "Jane", "affiliations": ["Univ A"]},
        ]
        result = extract_affiliations(authors)
        assert result == ["Univ A"]

    def test_extract_affiliations_empty_authors(self) -> None:
        """Should return empty list for no authors."""
        result = extract_affiliations([])
        assert result == []

    def test_extract_affiliations_whitespace(self) -> None:
        """Should strip whitespace."""
        authors = [{"name": "John", "affiliations": ["  Univ A  "]}]
        result = extract_affiliations(authors)
        assert result == ["Univ A"]

    def test_extract_affiliations_none_in_list(self) -> None:
        """Should filter out None values inside affiliations list."""
        authors = [{"name": "John", "affiliations": ["MIT", None, "Harvard"]}]
        result = extract_affiliations(authors)
        assert result == ["Harvard", "MIT"]

    def test_extract_affiliations_unique_sorted(self) -> None:
        """Should return unique sorted affiliations across all authors."""
        authors = [
            {"name": "John", "affiliations": ["MIT", "Harvard"]},
            {"name": "Jane", "affiliations": ["MIT", "Stanford"]},
        ]
        result = extract_affiliations(authors)
        assert result == ["Harvard", "MIT", "Stanford"]


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

        assert result["journal"] == "Nature"
        assert result["volume"] == "629"
        assert result["issue"] is None  # No issue in simple volume
        assert result["page_range"] == "123-130"
        assert result["page_first"] == "123"
        assert result["page_last"] == "130"

    def test_fallback_to_venue(self) -> None:
        """Test fallback to venue when journal name is missing."""
        journal = {"volume": "10"}

        result = extract_journal_info(journal, venue="Conference Proceedings")

        assert result["journal"] == "Conference Proceedings"
        assert result["volume"] == "10"
        assert result["issue"] is None
        assert result["page_range"] is None
        assert result["page_first"] is None
        assert result["page_last"] is None

    def test_venue_only(self) -> None:
        """Test when only venue is provided."""
        result = extract_journal_info(None, venue="ArXiv")

        assert result["journal"] == "ArXiv"
        assert result["volume"] is None
        assert result["issue"] is None
        assert result["page_range"] is None
        assert result["page_first"] is None
        assert result["page_last"] is None

    def test_empty_journal(self) -> None:
        """Test with empty journal dict."""
        result = extract_journal_info({}, venue="Fallback Venue")

        assert result["journal"] == "Fallback Venue"
        assert result["volume"] is None
        assert result["issue"] is None


class TestExtractOpenAccessInfo:
    """Tests for extract_open_access_info function.

    Tests the three-valued logic for is_oa:
    - True: Confirmed open access
    - False: Confirmed closed access
    - None: Unknown (API did not provide info)

    This distinction is important for downstream analytics to differentiate
    "we know it's closed" from "we don't know".
    """

    def test_extract_open_access_true_with_green_status(self) -> None:
        """Test open access with GREEN status is normalized to lowercase."""
        oa_pdf = {
            "url": "https://example.com/paper.pdf",
            "status": "GREEN",
        }

        result = extract_open_access_info(True, oa_pdf)

        assert result["is_oa"] is True
        assert result["url"] == "https://example.com/paper.pdf"
        assert result["oa_status"] == "green"

    def test_closed_access_explicit_false(self) -> None:
        """Test that explicit False gets 'closed' status."""
        result = extract_open_access_info(False, None)

        assert result["is_oa"] is False
        assert result["url"] is None
        assert result["oa_status"] == "closed"

    def test_unknown_access_none_preserved(self) -> None:
        """Test that None is_open_access is preserved as None (not converted to False).

        This is critical for analytics: None means "unknown", False means "closed".
        Converting None to False would misrepresent data quality.
        """
        result = extract_open_access_info(None, None)

        assert result["is_oa"] is None  # Preserved, not converted to False
        assert result["url"] is None
        assert result["oa_status"] is None  # Unknown, not "closed"

    def test_open_access_true_without_pdf(self) -> None:
        """Test open access True without PDF info."""
        result = extract_open_access_info(True, None)

        assert result["is_oa"] is True
        assert result["url"] is None
        assert result["oa_status"] is None  # No status available

    def test_false_with_green_pdf_status(self) -> None:
        """Test is_oa=False but PDF has GREEN status (edge case).

        The PDF status takes precedence over is_oa=False for oa_status.
        """
        oa_pdf = {"url": "https://example.com/paper.pdf", "status": "GREEN"}
        result = extract_open_access_info(False, oa_pdf)

        assert result["is_oa"] is False
        assert result["url"] == "https://example.com/paper.pdf"
        assert result["oa_status"] == "green"  # PDF status, not "closed"

    def test_none_with_green_pdf_status(self) -> None:
        """Test is_oa=None but PDF has GREEN status.

        When is_oa is unknown but PDF provides status, use PDF status.
        """
        oa_pdf = {"url": "https://example.com/paper.pdf", "status": "GREEN"}
        result = extract_open_access_info(None, oa_pdf)

        assert result["is_oa"] is None  # Still unknown
        assert result["url"] == "https://example.com/paper.pdf"
        assert result["oa_status"] == "green"  # From PDF

    def test_none_with_pdf_none_status(self) -> None:
        """Test is_oa=None with PDF that has no status.

        When both is_oa and PDF status are unknown, oa_status should be None.
        """
        oa_pdf = {"url": "https://example.com/paper.pdf", "status": None}
        result = extract_open_access_info(None, oa_pdf)

        assert result["is_oa"] is None
        assert result["url"] == "https://example.com/paper.pdf"
        assert result["oa_status"] is None  # Unknown, not "closed"

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

    def test_open_access_info__status_returns_none__949734fa(self) -> None:
        """Test that unknown OA status returns None."""
        oa_pdf = {"url": "https://example.com/paper.pdf", "status": "UNKNOWN"}
        result = extract_open_access_info(True, oa_pdf)
        assert result["oa_status"] is None

    def test_bronze_status_normalized(self) -> None:
        """Test that BRONZE status is normalized to lowercase."""
        oa_pdf = {"url": "https://example.com/paper.pdf", "status": "BRONZE"}
        result = extract_open_access_info(True, oa_pdf)
        assert result["oa_status"] == "bronze"

    def test_empty_pdf_dict(self) -> None:
        """Test with empty PDF dict (no url or status)."""
        result = extract_open_access_info(True, {})

        assert result["is_oa"] is True
        assert result["url"] is None
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

    def test_extract_tldr__extract_none__f3449907(self) -> None:
        """Test extracting from None."""
        result = extract_tldr(None)
        assert result is None

    def test_extract_tldr__extract_empty_dict__8c0ff7c5(self) -> None:
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

    def test_filter_none_elements(self) -> None:
        """Test that None elements are filtered out."""
        fields = ["Biology", None, "Medicine", None, "Genetics"]

        result = extract_fields_of_study(fields)

        assert result == ["Biology", "Medicine", "Genetics"]

    def test_filter_empty_string_elements(self) -> None:
        """Test that empty string elements are filtered out."""
        fields = ["Biology", "", "Medicine", "", "Genetics"]

        result = extract_fields_of_study(fields)

        assert result == ["Biology", "Medicine", "Genetics"]

    def test_filter_mixed_invalid_elements(self) -> None:
        """Test filtering both None and empty strings."""
        fields = ["Biology", None, "", "Medicine", None, ""]

        result = extract_fields_of_study(fields)

        assert result == ["Biology", "Medicine"]

    def test_max_count_applied_after_filtering(self) -> None:
        """Test that max_count is applied after filtering invalid elements."""
        fields = ["A", None, "B", "", "C", None, "D", "E"]

        result = extract_fields_of_study(fields, max_count=3)

        # Should filter first, then limit: ["A", "B", "C", "D", "E"][:3]
        assert result == ["A", "B", "C"]


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

    def test_normalize_oa_status__none_returns_none__6f2e95dd(self) -> None:
        """Test None returns None."""
        assert normalize_oa_status(None) is None

    def test_whitespace_trimmed(self) -> None:
        """Test whitespace is trimmed before normalization."""
        assert normalize_oa_status("  GOLD  ") == "gold"
        assert normalize_oa_status("\tgreen\n") == "green"


class TestExtractAuthorS2Ids:
    """Tests for extract_author_s2_ids function."""

    def test_extract_multiple_ids(self) -> None:
        """Test extracting multiple S2 author IDs."""
        authors = [
            {"authorId": "1234567890abcdef1234567890abcdef12345678", "name": "John"},
            {"authorId": "abcdef1234567890abcdef1234567890abcdef12", "name": "Jane"},
        ]
        result = extract_author_s2_ids(authors)
        assert result == [
            "1234567890abcdef1234567890abcdef12345678",
            "abcdef1234567890abcdef1234567890abcdef12",
        ]

    def test_skip_none_ids(self) -> None:
        """Test that None author IDs are skipped."""
        authors = [
            {"authorId": "1234567890abcdef1234567890abcdef12345678", "name": "John"},
            {"authorId": None, "name": "Jane"},
            {"authorId": "abcdef1234567890abcdef1234567890abcdef12", "name": "Bob"},
        ]
        result = extract_author_s2_ids(authors)
        assert result == [
            "1234567890abcdef1234567890abcdef12345678",
            "abcdef1234567890abcdef1234567890abcdef12",
        ]

    def test_skip_missing_ids(self) -> None:
        """Test that missing authorId keys are skipped."""
        authors = [
            {"authorId": "1234567890abcdef1234567890abcdef12345678", "name": "John"},
            {"name": "Jane"},  # No authorId key
        ]
        result = extract_author_s2_ids(authors)
        assert result == ["1234567890abcdef1234567890abcdef12345678"]

    def test_extract_author_s2_ids__empty_list__d807162a(self) -> None:
        """Test with empty list."""
        assert extract_author_s2_ids([]) == []

    def test_extract_author_s2_ids__none_input__b601f4f3(self) -> None:
        """Test with None input."""
        assert extract_author_s2_ids(None) == []

    def test_strip_whitespace(self) -> None:
        """Test that IDs are stripped of whitespace."""
        authors = [{"authorId": "  abc123  ", "name": "John"}]
        result = extract_author_s2_ids(authors)
        assert result == ["abc123"]


class TestExtractAuthorOrcids:
    """Tests for extract_author_orcids function."""

    def test_extract_orcids(self) -> None:
        """Test extracting ORCID identifiers."""
        authors = [
            {"name": "John", "externalIds": {"ORCID": "0000-0001-2345-6789"}},
            {"name": "Jane", "externalIds": {"ORCID": "0000-0002-3456-7890"}},
        ]
        result = extract_author_orcids(authors)
        assert result == ["0000-0001-2345-6789", "0000-0002-3456-7890"]

    def test_placeholder_for_missing_orcid(self) -> None:
        """Test that empty string is used for missing ORCID."""
        authors = [
            {"name": "John", "externalIds": {"ORCID": "0000-0001-2345-6789"}},
            {"name": "Jane", "externalIds": None},
            {"name": "Bob", "externalIds": {"DBLP": "some-dblp-id"}},
        ]
        result = extract_author_orcids(authors)
        assert result == ["0000-0001-2345-6789", "", ""]

    def test_missing_external_ids_key(self) -> None:
        """Test authors without externalIds key."""
        authors = [
            {"name": "John", "externalIds": {"ORCID": "0000-0001-2345-6789"}},
            {"name": "Jane"},  # No externalIds key
        ]
        result = extract_author_orcids(authors)
        assert result == ["0000-0001-2345-6789", ""]

    def test_extract_author_orcids__empty_list__6e9b61d5(self) -> None:
        """Test with empty list."""
        assert extract_author_orcids([]) == []

    def test_extract_author_orcids__none_input__1759f883(self) -> None:
        """Test with None input."""
        assert extract_author_orcids(None) == []

    def test_extract_author_orcids__strip_whitespace__bbe2400c(self) -> None:
        """Test that ORCIDs are stripped of whitespace."""
        authors = [
            {"name": "John", "externalIds": {"ORCID": "  0000-0001-2345-6789  "}}
        ]
        result = extract_author_orcids(authors)
        assert result == ["0000-0001-2345-6789"]


class TestExtractAuthorHIndices:
    """Tests for extract_author_h_indices function."""

    def test_extract_h_indices(self) -> None:
        """Test extracting h-index values."""
        authors = [
            {"name": "John", "hIndex": 45},
            {"name": "Jane", "hIndex": 23},
        ]
        result = extract_author_h_indices(authors)
        assert result == [45, 23]

    def test_none_for_missing_h_index(self) -> None:
        """Test that None is returned for missing h-index."""
        authors = [
            {"name": "John", "hIndex": 45},
            {"name": "Jane", "hIndex": None},
            {"name": "Bob"},  # No hIndex key
        ]
        result = extract_author_h_indices(authors)
        assert result == [45, None, None]

    def test_zero_h_index(self) -> None:
        """Test that zero h-index is valid."""
        authors = [{"name": "John", "hIndex": 0}]
        result = extract_author_h_indices(authors)
        assert result == [0]

    def test_negative_h_index_treated_as_none(self) -> None:
        """Test that negative h-index is treated as None."""
        authors = [{"name": "John", "hIndex": -1}]
        result = extract_author_h_indices(authors)
        assert result == [None]

    def test_author_h_indices__empty_list__5b311abc(self) -> None:
        """Test with empty list."""
        assert extract_author_h_indices([]) == []

    def test_author_h_indices__none_input__fabb019e(self) -> None:
        """Test with None input."""
        assert extract_author_h_indices(None) == []


class TestExtractCitationContexts:
    """Tests for extract_citation_contexts function."""

    def test_extract_contexts(self) -> None:
        """Test extracting citation context sentences."""
        citations = [
            {
                "paperId": "abc123",
                "contexts": ["The method in [1] shows...", "As shown by [1]..."],
            },
            {"paperId": "def456", "contexts": ["Building on [2]..."]},
        ]
        result = extract_citation_contexts(citations)
        assert result == [
            "The method in [1] shows...",
            "As shown by [1]...",
            "Building on [2]...",
        ]

    def test_max_contexts_limit(self) -> None:
        """Test max_contexts parameter limits results."""
        citations = [
            {"paperId": "abc123", "contexts": ["Context 1", "Context 2", "Context 3"]},
            {"paperId": "def456", "contexts": ["Context 4", "Context 5"]},
        ]
        result = extract_citation_contexts(citations, max_contexts=3)
        assert result == ["Context 1", "Context 2", "Context 3"]

    def test_skip_empty_contexts(self) -> None:
        """Test that empty context strings are skipped."""
        citations = [
            {"paperId": "abc123", "contexts": ["Valid context", "", "  ", "Another"]},
        ]
        result = extract_citation_contexts(citations)
        assert result == ["Valid context", "Another"]

    def test_skip_none_contexts(self) -> None:
        """Test that None contexts are skipped."""
        citations = [
            {"paperId": "abc123", "contexts": ["Valid", None, "Also valid"]},
        ]
        result = extract_citation_contexts(citations)
        assert result == ["Valid", "Also valid"]

    def test_missing_contexts_key(self) -> None:
        """Test citations without contexts key."""
        citations = [
            {"paperId": "abc123", "contexts": ["Has context"]},
            {"paperId": "def456"},  # No contexts key
        ]
        result = extract_citation_contexts(citations)
        assert result == ["Has context"]

    def test_none_contexts_field(self) -> None:
        """Test when contexts field is None."""
        citations = [
            {"paperId": "abc123", "contexts": None},
            {"paperId": "def456", "contexts": ["Valid"]},
        ]
        result = extract_citation_contexts(citations)
        assert result == ["Valid"]

    def test_citation_contexts__empty_list__2f0e3363(self) -> None:
        """Test with empty list."""
        assert extract_citation_contexts([]) == []

    def test_citation_contexts__none_input__fc647235(self) -> None:
        """Test with None input."""
        assert extract_citation_contexts(None) == []

    def test_citation_contexts__strip_whitespace__4e725ede(self) -> None:
        """Test that contexts are stripped of whitespace."""
        citations = [{"paperId": "abc", "contexts": ["  Trimmed context  "]}]
        result = extract_citation_contexts(citations)
        assert result == ["Trimmed context"]


class TestParseVolumeIssue:
    """Tests for parse_volume_issue function.

    Semantic Scholar API sometimes returns combined volume/issue in the
    volume field (e.g., "32 4" for volume 32, issue 4).
    """

    def test_space_separated(self) -> None:
        """Test S2 format: '32 4' → vol=32, issue=4."""
        assert parse_volume_issue("32 4") == ("32", "4")

    def test_simple_volume(self) -> None:
        """Test single volume number (no issue)."""
        assert parse_volume_issue("523") == ("523", None)

    def test_parentheses_format(self) -> None:
        """Test '40(3)' format."""
        assert parse_volume_issue("40(3)") == ("40", "3")

    def test_parentheses_with_space(self) -> None:
        """Test '40 (3)' format with space."""
        assert parse_volume_issue("40 (3)") == ("40", "3")

    def test_vol_no_format(self) -> None:
        """Test 'Vol. 32, No. 4' format."""
        assert parse_volume_issue("Vol. 32, No. 4") == ("32", "4")

    def test_vol_no_format_no_punctuation(self) -> None:
        """Test 'Vol 32 No 4' format without punctuation."""
        assert parse_volume_issue("Vol 32 No 4") == ("32", "4")

    def test_colon_separated(self) -> None:
        """Test '32:4' format."""
        assert parse_volume_issue("32:4") == ("32", "4")

    def test_parse_volume_issue__none_input__0078931f(self) -> None:
        """Test with None input."""
        assert parse_volume_issue(None) == (None, None)

    def test_parse_volume_issue__empty_string__0e731ccb(self) -> None:
        """Test with empty string."""
        assert parse_volume_issue("") == (None, None)

    def test_whitespace_only(self) -> None:
        """Test with whitespace-only string."""
        assert parse_volume_issue("   ") == (None, None)

    def test_non_numeric_volume(self) -> None:
        """Test with non-numeric volume (preserved as-is)."""
        assert parse_volume_issue("Suppl 1") == ("Suppl 1", None)

    def test_real_world_example(self) -> None:
        """Test real-world S2 data: '32 4' from Journal of Medicinal Chemistry."""
        assert parse_volume_issue("32 4") == ("32", "4")


class TestParsePageRange:
    """Tests for parse_page_range with abbreviated expansion.

    Academic publishing often abbreviates page ranges:
    - "737-9" means 737-739 (not 737-9)
    - "737-39" means 737-739
    """

    def test_abbreviated_single_digit(self) -> None:
        """737-9 → (737, 739)."""
        assert parse_page_range("737-9") == ("737", "739")

    def test_abbreviated_two_digits(self) -> None:
        """737-39 → (737, 739)."""
        assert parse_page_range("737-39") == ("737", "739")

    def test_full_range(self) -> None:
        """737-839 → (737, 839) - no expansion needed."""
        assert parse_page_range("737-839") == ("737", "839")

    def test_full_range_same_length(self) -> None:
        """123-145 → (123, 145)."""
        assert parse_page_range("123-145") == ("123", "145")

    def test_single_page(self) -> None:
        """123 → (123, None)."""
        assert parse_page_range("123") == ("123", None)

    def test_whitespace_handling(self) -> None:
        """Handles whitespace and newlines."""
        assert parse_page_range("\n  737-9\n  ") == ("737", "739")

    def test_space_around_dash(self) -> None:
        """Handles space around dash - expansion still works."""
        assert parse_page_range("737 - 9") == ("737", "739")

    def test_en_dash(self) -> None:
        """Handles en-dash (U+2013)."""
        assert parse_page_range("737\u20139") == ("737", "739")

    def test_em_dash(self) -> None:
        """Handles em-dash (U+2014)."""
        assert parse_page_range("737\u20149") == ("737", "739")

    def test_supplement_pages(self) -> None:
        """Handles supplement page numbers like S1-S5."""
        assert parse_page_range("S1-S5") == ("S1", "S5")

    def test_rollover_case(self) -> None:
        """199-3 → (199, 203) - not (199, 193)."""
        assert parse_page_range("199-3") == ("199", "203")

    def test_parse_page_range__none_input__17cdf064(self) -> None:
        """Test with None input."""
        assert parse_page_range(None) == (None, None)

    def test_parse_page_range__empty_string__d37f5191(self) -> None:
        """Test with empty string."""
        assert parse_page_range("") == (None, None)

    def test_parse_page_range__whitespace_only__c066e6c5(self) -> None:
        """Test with whitespace-only string."""
        assert parse_page_range("   ") == (None, None)

    def test_four_digit_pages(self) -> None:
        """1234-56 → (1234, 1256)."""
        assert parse_page_range("1234-56") == ("1234", "1256")

    def test_parse_page_range__real_world_example__a6981d84(self) -> None:
        """Test real-world S2 data with newlines: '\\n  737-9\\n  '."""
        assert parse_page_range("\n          737-9\n        ") == ("737", "739")


class TestExtractJournalInfoIntegration:
    """Integration tests for extract_journal_info with parsing.

    Tests the complete flow from raw API data to parsed fields.
    """

    def test_combined_volume_issue_and_abbreviated_pages(self) -> None:
        """Test parsing combined volume/issue and abbreviated pages."""
        journal = {
            "name": "Journal of medicinal chemistry",
            "volume": "32 4",
            "pages": "\n          737-9\n        ",
        }

        result = extract_journal_info(journal, None)

        assert result["journal"] == "Journal of medicinal chemistry"
        assert result["volume"] == "32"
        assert result["issue"] == "4"
        assert result["page_range"] == "737-9"  # Cleaned
        assert result["page_first"] == "737"
        assert result["page_last"] == "739"  # Expanded

    def test_simple_volume_full_pages(self) -> None:
        """Test simple volume with full page range."""
        journal = {
            "name": "Nature",
            "volume": "523",
            "pages": "561-567",
        }

        result = extract_journal_info(journal, "Nature")

        assert result["journal"] == "Nature"
        assert result["volume"] == "523"
        assert result["issue"] is None
        assert result["page_range"] == "561-567"
        assert result["page_first"] == "561"
        assert result["page_last"] == "567"

    def test_venue_fallback(self) -> None:
        """Test venue fallback when journal name is missing."""
        journal = {"volume": "10"}

        result = extract_journal_info(journal, "Conference Proceedings")

        assert result["journal"] == "Conference Proceedings"
        assert result["volume"] == "10"
        assert result["issue"] is None

    def test_none_journal(self) -> None:
        """Test with None journal."""
        result = extract_journal_info(None, "ArXiv")

        assert result["journal"] == "ArXiv"
        assert result["volume"] is None
        assert result["issue"] is None
        assert result["page_range"] is None
        assert result["page_first"] is None
        assert result["page_last"] is None

    def test_extract_journal_info__empty_journal__38bad73c(self) -> None:
        """Test with empty journal dict."""
        result = extract_journal_info({}, "Fallback Venue")

        assert result["journal"] == "Fallback Venue"
        assert result["volume"] is None
        assert result["issue"] is None
