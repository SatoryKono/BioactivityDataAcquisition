# tests/unit/application/pipelines/semanticscholar/test_extractors.py
"""Unit tests for Semantic Scholar field extractors."""

from __future__ import annotations

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
    validate_year,
)
from bioetl.application.pipelines.semanticscholar.sanitizers import (
    sanitize_arxiv_id,
    sanitize_dblp_id,
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
        assert result["pmcid"] == "PMC1234567"
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

    def test_extract_affiliations_deduplication(self) -> None:
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

    def test_empty_list(self) -> None:
        """Test with empty list."""
        assert extract_author_s2_ids([]) == []

    def test_none_input(self) -> None:
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

    def test_empty_list(self) -> None:
        """Test with empty list."""
        assert extract_author_orcids([]) == []

    def test_none_input(self) -> None:
        """Test with None input."""
        assert extract_author_orcids(None) == []

    def test_strip_whitespace(self) -> None:
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

    def test_empty_list(self) -> None:
        """Test with empty list."""
        assert extract_author_h_indices([]) == []

    def test_none_input(self) -> None:
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

    def test_empty_list(self) -> None:
        """Test with empty list."""
        assert extract_citation_contexts([]) == []

    def test_none_input(self) -> None:
        """Test with None input."""
        assert extract_citation_contexts(None) == []

    def test_strip_whitespace(self) -> None:
        """Test that contexts are stripped of whitespace."""
        citations = [{"paperId": "abc", "contexts": ["  Trimmed context  "]}]
        result = extract_citation_contexts(citations)
        assert result == ["Trimmed context"]


class TestSanitizeArxivId:
    """Tests for sanitize_arxiv_id function."""

    def test_valid_new_format(self) -> None:
        """Test valid new format ArXiv IDs (post-2007)."""
        assert sanitize_arxiv_id("2301.12345") == "2301.12345"
        assert sanitize_arxiv_id("0704.0001") == "0704.0001"
        assert sanitize_arxiv_id("2106.15928") == "2106.15928"

    def test_valid_new_format_with_version(self) -> None:
        """Test valid new format with version suffix."""
        assert sanitize_arxiv_id("2301.12345v1") == "2301.12345v1"
        assert sanitize_arxiv_id("2301.12345v2") == "2301.12345v2"
        assert sanitize_arxiv_id("2106.15928v12") == "2106.15928v12"

    def test_valid_old_format(self) -> None:
        """Test valid old format ArXiv IDs (pre-2007)."""
        assert sanitize_arxiv_id("hep-ph/9912271") == "hep-ph/9912271"
        assert sanitize_arxiv_id("cs/0001007") == "cs/0001007"
        assert sanitize_arxiv_id("math/0001001") == "math/0001001"

    def test_valid_old_format_with_subcategory(self) -> None:
        """Test valid old format with subcategory."""
        assert sanitize_arxiv_id("cs.AI/0001007") == "cs.AI/0001007"
        assert sanitize_arxiv_id("math.CO/0001001") == "math.CO/0001001"

    def test_valid_old_format_with_version(self) -> None:
        """Test valid old format with version."""
        assert sanitize_arxiv_id("hep-ph/9912271v1") == "hep-ph/9912271v1"
        assert sanitize_arxiv_id("hep-ph/9912271v2") == "hep-ph/9912271v2"

    def test_invalid_format_returns_none(self) -> None:
        """Test invalid formats return None."""
        assert sanitize_arxiv_id("invalid-id") is None
        assert sanitize_arxiv_id("12345") is None
        assert sanitize_arxiv_id("abc.12345") is None
        assert sanitize_arxiv_id("not/a/valid/id") is None

    def test_empty_string_returns_none(self) -> None:
        """Test empty string returns None."""
        assert sanitize_arxiv_id("") is None
        assert sanitize_arxiv_id("   ") is None

    def test_none_returns_none(self) -> None:
        """Test None returns None."""
        assert sanitize_arxiv_id(None) is None

    def test_whitespace_trimmed(self) -> None:
        """Test whitespace is trimmed."""
        assert sanitize_arxiv_id("  2301.12345  ") == "2301.12345"
        assert sanitize_arxiv_id("\t2301.12345\n") == "2301.12345"


class TestSanitizeDblpId:
    """Tests for sanitize_dblp_id function."""

    def test_valid_conference_format(self) -> None:
        """Test valid conference paper DBLP IDs."""
        assert sanitize_dblp_id("conf/nips/SmithJ21") == "conf/nips/SmithJ21"
        assert sanitize_dblp_id("conf/icml/DoeA22") == "conf/icml/DoeA22"
        assert sanitize_dblp_id("conf/aaai/LeeK20") == "conf/aaai/LeeK20"

    def test_valid_journal_format(self) -> None:
        """Test valid journal paper DBLP IDs."""
        assert sanitize_dblp_id("journals/jmlr/SmithJ21") == "journals/jmlr/SmithJ21"
        assert sanitize_dblp_id("journals/nature/DoeA22") == "journals/nature/DoeA22"
        assert (
            sanitize_dblp_id("journals/corr/abs-2301-12345")
            == "journals/corr/abs-2301-12345"
        )

    def test_valid_book_format(self) -> None:
        """Test valid book DBLP IDs."""
        assert sanitize_dblp_id("books/daglib/0028988") == "books/daglib/0028988"
        assert sanitize_dblp_id("books/sp/Smith21") == "books/sp/Smith21"

    def test_valid_with_underscores(self) -> None:
        """Test valid DBLP IDs with underscores."""
        assert sanitize_dblp_id("conf/nips/Smith_Lee21") == "conf/nips/Smith_Lee21"

    def test_valid_with_hyphens(self) -> None:
        """Test valid DBLP IDs with hyphens."""
        assert (
            sanitize_dblp_id("journals/corr/abs-2301-12345")
            == "journals/corr/abs-2301-12345"
        )

    def test_invalid_format_returns_none(self) -> None:
        """Test invalid formats return None."""
        assert sanitize_dblp_id("invalid") is None
        assert sanitize_dblp_id("just-text") is None
        assert sanitize_dblp_id("CONF/nips/Smith") is None  # Must start with lowercase

    def test_empty_string_returns_none(self) -> None:
        """Test empty string returns None."""
        assert sanitize_dblp_id("") is None
        assert sanitize_dblp_id("   ") is None

    def test_none_returns_none(self) -> None:
        """Test None returns None."""
        assert sanitize_dblp_id(None) is None

    def test_whitespace_trimmed(self) -> None:
        """Test whitespace is trimmed."""
        assert sanitize_dblp_id("  conf/nips/SmithJ21  ") == "conf/nips/SmithJ21"
        assert sanitize_dblp_id("\tconf/nips/SmithJ21\n") == "conf/nips/SmithJ21"
