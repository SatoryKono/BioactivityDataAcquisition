"""Unit tests for CrossRef field extractors.

Tests the pure functions in extractors.py module.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from bioetl.application.pipelines.crossref.extractors import (
    extract_affiliations,
    extract_author_details,
    extract_author_orcids,
    extract_authors,
    extract_content_domain,
    extract_dates,
    extract_issn_by_type,
    extract_journal_info,
    extract_license_url,
    extract_page_info,
    extract_published_date,
    extract_references,
)

LEGACY_HTTP_ORCID = "http" + "://orcid.org/0000-0001-2345-6789"


class TestExtractAuthors:
    """Tests for extract_authors function."""

    def test_extract_authors_given_and_family(self) -> None:
        """Should extract authors with both given and family names."""
        publication = {
            "author": [
                {"given": "John", "family": "Doe"},
                {"given": "Jane", "family": "Smith"},
            ]
        }
        result = extract_authors(publication)
        assert result == ["John Doe", "Jane Smith"]

    def test_extract_authors_family_only(self) -> None:
        """Should extract authors with only family name."""
        publication = {"author": [{"family": "Anonymous"}]}
        result = extract_authors(publication)
        assert result == ["Anonymous"]

    def test_extract_authors_given_only(self) -> None:
        """Should extract authors with only given name (mononym)."""
        publication = {"author": [{"given": "Madonna"}]}
        result = extract_authors(publication)
        assert result == ["Madonna"]

    def test_extract_authors__authors_empty_list__5ffa2bb2(self) -> None:
        """Should return empty list for empty author list."""
        publication = {"author": []}
        result = extract_authors(publication)
        assert result == []

    def test_extract_authors__authors_missing_key__71ff2257(self) -> None:
        """Should return empty list when author key is missing."""
        publication = {}
        result = extract_authors(publication)
        assert result == []

    def test_extract_authors__strips_whitespace__354d02da(self) -> None:
        """Should strip whitespace from author names."""
        publication = {"author": [{"given": "  John  ", "family": "  Doe  "}]}
        result = extract_authors(publication)
        assert result == ["John Doe"]

    def test_extract_authors_skips_empty_names(self) -> None:
        """Should skip authors with empty given and family names."""
        publication = {
            "author": [
                {"given": "", "family": ""},
                {"given": "Valid", "family": "Author"},
            ]
        }
        result = extract_authors(publication)
        assert result == ["Valid Author"]

    def test_extract_authors_mixed_formats(self) -> None:
        """Should handle mixed author formats in same list."""
        publication = {
            "author": [
                {"given": "First", "family": "Last"},
                {"family": "OnlyFamily"},
                {"given": "OnlyGiven"},
            ]
        }
        result = extract_authors(publication)
        assert result == ["First Last", "OnlyFamily", "OnlyGiven"]

    def test_extract_authors_organization(self) -> None:
        """Should extract organization authors with 'name' field."""
        publication = {"author": [{"name": "World Health Organization"}]}
        result = extract_authors(publication)
        assert result == ["World Health Organization"]

    def test_extract_authors_mixed_personal_and_org(self) -> None:
        """Should handle mixed personal and organizational authors."""
        publication = {
            "author": [
                {"given": "John", "family": "Doe"},
                {"name": "World Health Organization"},
                {"family": "Anonymous"},
            ]
        }
        result = extract_authors(publication)
        assert result == ["John Doe", "World Health Organization", "Anonymous"]

    def test_extract_authors_org_with_whitespace(self) -> None:
        """Should strip whitespace from organization names."""
        publication = {"author": [{"name": "  WHO  "}]}
        result = extract_authors(publication)
        assert result == ["WHO"]

    def test_extract_authors_empty_org_name_skipped(self) -> None:
        """Should skip organizations with empty name field."""
        publication = {
            "author": [
                {"name": ""},
                {"name": "   "},
                {"given": "Valid", "family": "Author"},
            ]
        }
        result = extract_authors(publication)
        assert result == ["Valid Author"]


class TestExtractAffiliations:
    """Tests for extract_affiliations function."""

    def test_extract_affiliations_dict_format(self) -> None:
        """Should extract affiliations from dict format."""
        pub = {
            "author": [
                {"affiliation": [{"name": "University A"}]},
                {"affiliation": [{"name": "University B"}]},
            ]
        }
        result = extract_affiliations(pub)
        assert result == ["University A", "University B"]

    def test_extract_affiliations_string_format(self) -> None:
        """Should extract affiliations from string format."""
        pub = {"author": [{"affiliation": ["University A", "University B"]}]}
        result = extract_affiliations(pub)
        assert result == ["University A", "University B"]

    def test_extract_affiliations_mixed_format(self) -> None:
        """Should handle mixed dict and string formats."""
        pub = {
            "author": [
                {"affiliation": [{"name": "University A"}]},
                {"affiliation": ["University B"]},
            ]
        }
        result = extract_affiliations(pub)
        assert result == ["University A", "University B"]

    def test_extract_affiliations_deduplication(self) -> None:
        """Should deduplicate affiliations."""
        pub = {
            "author": [
                {"affiliation": [{"name": "University A"}]},
                {"affiliation": [{"name": "University A"}]},
            ]
        }
        result = extract_affiliations(pub)
        assert result == ["University A"]

    def test_extract_affiliations_empty(self) -> None:
        """Should return empty list if no authors/affiliations."""
        result = extract_affiliations({})
        assert result == []

    def test_extract_affiliations_invalid_author(self) -> None:
        """Should skip invalid author entries."""
        pub = {"author": ["not_dict"]}
        result = extract_affiliations(pub)
        assert result == []


class TestExtractLicenseUrl:
    """Tests for extract_license_url function."""

    def test_extract_license_url_single(self) -> None:
        """Should extract license URL from single license."""
        publication = {
            "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}]
        }
        result = extract_license_url(publication)
        assert result == "https://creativecommons.org/licenses/by/4.0/"

    def test_extract_license_url_multiple(self) -> None:
        """Should return first license URL when multiple present."""
        publication = {
            "license": [
                {"URL": "https://license1.com"},
                {"URL": "https://license2.com"},
            ]
        }
        result = extract_license_url(publication)
        assert result == "https://license1.com"

    def test_extract_license_url__url_empty_list__1c1eceff(self) -> None:
        """Should return None for empty license list."""
        publication = {"license": []}
        result = extract_license_url(publication)
        assert result is None

    def test_extract_license_url_missing_key(self) -> None:
        """Should return None when license key is missing."""
        publication = {}
        result = extract_license_url(publication)
        assert result is None

    def test_extract_license_url_missing_url_field(self) -> None:
        """Should return None when URL field is missing."""
        publication = {"license": [{"other": "data"}]}
        result = extract_license_url(publication)
        assert result is None


class TestExtractJournalInfo:
    """Tests for extract_journal_info function."""

    def test_extract_journal_info_complete(self) -> None:
        """Should extract all journal fields."""
        publication = {
            "container-title": ["Nature", "Nature Publishing Group"],
            "ISSN": ["0028-0836", "1476-4687"],
            "publisher": "Springer Nature",
        }
        result = extract_journal_info(publication)
        assert result == {
            "journal": "Nature",
            "issn": "0028-0836",
            "issn_list": ["0028-0836", "1476-4687"],
            "publisher": "Springer Nature",
        }

    def test_extract_journal_info_partial(self) -> None:
        """Should handle missing fields gracefully."""
        publication = {"container-title": ["Nature"]}
        result = extract_journal_info(publication)
        assert result["journal"] == "Nature"
        assert result["issn"] is None
        assert result["issn_list"] is None
        assert result["publisher"] is None

    def test_extract_journal_info_empty(self) -> None:
        """Should return defaults for empty publication."""
        result = extract_journal_info({})
        assert result == {
            "journal": None,
            "issn": None,
            "issn_list": None,
            "publisher": None,
        }

    def test_extract_journal_info_empty_container_title(self) -> None:
        """Should return None for empty container-title list."""
        publication = {"container-title": []}
        result = extract_journal_info(publication)
        assert result["journal"] is None


class TestExtractPageInfo:
    """Tests for extract_page_info function."""

    def test_extract_page_info_complete(self) -> None:
        """Should extract all page fields."""
        publication = {"volume": "42", "issue": "3", "page": "123-145"}
        result = extract_page_info(publication)
        assert result == {
            "volume": "42",
            "issue": "3",
            "page_first": "123",
            "page_last": "145",
        }

    def test_extract_page_info_single_page(self) -> None:
        """Should handle single page number."""
        publication = {"page": "42"}
        result = extract_page_info(publication)
        assert result["page_first"] == "42"
        assert result["page_last"] is None

    def test_extract_page_info_missing_fields(self) -> None:
        """Should return None for missing fields."""
        result = extract_page_info({})
        assert result == {
            "volume": None,
            "issue": None,
            "page_first": None,
            "page_last": None,
        }

    def test_extract_page_info_partial(self) -> None:
        """Should handle partial page info."""
        publication = {"volume": "10", "page": "1-50"}
        result = extract_page_info(publication)
        assert result["volume"] == "10"
        assert result["issue"] is None
        assert result["page_first"] == "1"
        assert result["page_last"] == "50"

    def test_extract_page_info_article_number(self) -> None:
        """Should handle article numbers (e-pages)."""
        publication = {"page": "e12345"}
        result = extract_page_info(publication)
        assert result["page_first"] == "e12345"
        assert result["page_last"] is None


class TestExtractDates:
    """Tests for extract_dates function.

    Uses end-of-period normalization for partial dates:
    - Month-only dates use last day of month
    - Year-only dates use December 31st
    """

    def test_extract_dates_complete(self) -> None:
        """Should extract both date fields."""
        publication = {
            "published-print": {"date-parts": [[2023, 6, 15]]},
            "published-online": {"date-parts": [[2023, 5, 1]]},
        }
        result = extract_dates(publication)
        assert result == {
            "published_print": "2023-06-15",
            "published_online": "2023-05-01",
        }

    def test_extract_dates_partial_date(self) -> None:
        """Should handle partial dates with end-of-period normalization."""
        publication = {
            "published-print": {"date-parts": [[2023, 6]]},  # June -> 30 days
            "published-online": {"date-parts": [[2023]]},  # Year -> Dec 31
        }
        result = extract_dates(publication)
        assert result["published_print"] == "2023-06-30"  # Last day of June
        assert result["published_online"] == "2023-12-31"  # Last day of year

    def test_extract_dates_empty(self) -> None:
        """Should return None for empty publication."""
        result = extract_dates({})
        assert result == {"published_print": None, "published_online": None}

    def test_extract_dates_missing_date_parts(self) -> None:
        """Should handle missing date-parts."""
        publication = {"published-print": {}, "published-online": {}}
        result = extract_dates(publication)
        assert result == {"published_print": None, "published_online": None}

    def test_extract_dates_invalid_format(self) -> None:
        """Should handle non-dict date fields gracefully."""
        publication = {
            "published-print": "invalid",
            "published-online": ["also invalid"],
        }
        result = extract_dates(publication)
        assert result == {"published_print": None, "published_online": None}


class TestExtractContentDomain:
    """Tests for extract_content_domain function."""

    def test_full_content_domain(self) -> None:
        """Should extract complete content-domain metadata."""
        record = {
            "content-domain": {
                "domain": ["nature.com", "springernature.com"],
                "crossmark-restriction": True,
            }
        }
        result = extract_content_domain(record)
        assert result["content_domain_domains"] == ["nature.com", "springernature.com"]
        assert result["content_domain_crossmark_restriction"] is True

    def test_empty_record(self) -> None:
        """Should return defaults for empty record."""
        result = extract_content_domain({})
        assert result["content_domain_domains"] == []
        assert result["content_domain_crossmark_restriction"] is None

    def test_empty_domain_list(self) -> None:
        """Should handle empty domain list."""
        record = {"content-domain": {"domain": [], "crossmark-restriction": False}}
        result = extract_content_domain(record)
        assert result["content_domain_domains"] == []
        assert result["content_domain_crossmark_restriction"] is False

    def test_invalid_content_domain_type(self) -> None:
        """Should handle non-dict content-domain gracefully."""
        record = {"content-domain": "invalid"}
        result = extract_content_domain(record)
        assert result["content_domain_domains"] == []
        assert result["content_domain_crossmark_restriction"] is None

    def test_none_domain_list(self) -> None:
        """Should handle None domain list."""
        record = {"content-domain": {"domain": None}}
        result = extract_content_domain(record)
        assert result["content_domain_domains"] == []


class TestExtractIssnByType:
    """Tests for extract_issn_by_type function."""

    @pytest.mark.parametrize(
        ("input_data", "expected"),
        [
            pytest.param(
                {"issn-type": [{"value": "0006-291X", "type": "print"}]},
                {"issn_print": "0006-291X", "issn_electronic": None},
                id="print_only",
            ),
            pytest.param(
                {"issn-type": [{"value": "1090-2104", "type": "electronic"}]},
                {"issn_print": None, "issn_electronic": "1090-2104"},
                id="electronic_only",
            ),
            pytest.param(
                {
                    "issn-type": [
                        {"value": "0006-291X", "type": "print"},
                        {"value": "1090-2104", "type": "electronic"},
                    ]
                },
                {"issn_print": "0006-291X", "issn_electronic": "1090-2104"},
                id="both_types",
            ),
            pytest.param(
                {},
                {"issn_print": None, "issn_electronic": None},
                id="empty_record",
            ),
            pytest.param(
                {"issn-type": "invalid"},
                {"issn_print": None, "issn_electronic": None},
                id="invalid_type",
            ),
            pytest.param(
                {"issn-type": [{"value": "1234-5678"}]},
                {"issn_print": None, "issn_electronic": None},
                id="missing_type_field",
            ),
            pytest.param(
                {"issn-type": [None, {"value": "0006-291X", "type": "print"}]},
                {"issn_print": "0006-291X", "issn_electronic": None},
                id="none_in_list",
            ),
        ],
    )
    def test_extract_issn_by_type(self, input_data: dict, expected: dict) -> None:
        """Should extract ISSN values by type correctly."""
        result = extract_issn_by_type(input_data)
        assert result == expected

    def test_duplicate_types_takes_first(self) -> None:
        """Should take first occurrence when duplicates exist."""
        record = {
            "issn-type": [
                {"value": "1111-1111", "type": "print"},
                {"value": "2222-2222", "type": "print"},
            ]
        }
        result = extract_issn_by_type(record)
        assert result["issn_print"] == "1111-1111"


class TestExtractPublishedDate:
    """Tests for extract_published_date function."""

    def test_full_date(self) -> None:
        """Should extract full date."""
        record = {"published": {"date-parts": [[2023, 6, 15]]}}
        result = extract_published_date(record)
        assert result == "2023-06-15"

    def test_year_month_only(self) -> None:
        """Should handle year-month with end-of-month normalization."""
        record = {"published": {"date-parts": [[2023, 6]]}}
        result = extract_published_date(record)
        assert result == "2023-06-30"

    def test_year_only(self) -> None:
        """Should handle year-only with end-of-year normalization."""
        record = {"published": {"date-parts": [[2023]]}}
        result = extract_published_date(record)
        assert result == "2023-12-31"

    def test_extract_published_date__empty_record__a7949e0f(self) -> None:
        """Should return None for empty record."""
        result = extract_published_date({})
        assert result is None

    def test_invalid_published_type(self) -> None:
        """Should return None for non-dict published field."""
        record = {"published": "2023-06-15"}
        result = extract_published_date(record)
        assert result is None

    def test_missing_date_parts(self) -> None:
        """Should return None when date-parts is missing."""
        record = {"published": {}}
        result = extract_published_date(record)
        assert result is None


class TestExtractAuthorDetails:
    """Tests for extract_author_details function."""

    def test_extract_full_author_details(self) -> None:
        """Should extract complete author details with all fields."""
        publication = {
            "author": [
                {
                    "given": "John",
                    "family": "Doe",
                    "ORCID": "https://ormolecule_id.org/0000-0001-2345-6789",
                    "authenticated-ormolecule_id": True,
                    "sequence": "first",
                    "affiliation": [{"name": "Harvard University"}],
                }
            ]
        }
        result = extract_author_details(publication)
        assert len(result) == 1
        assert result[0]["given"] == "John"
        assert result[0]["family"] == "Doe"
        assert result[0]["name"] is None
        assert result[0]["ormolecule_id"] == "0000-0001-2345-6789"
        assert result[0]["authenticated_ormolecule_id"] is True
        assert result[0]["sequence"] == "first"
        assert result[0]["affiliations"] == ["Harvard University"]

    def test_extract_author_with_ormolecule_id_id_only(self) -> None:
        """Should handle ORCID without URL prefix."""
        publication = {
            "author": [
                {
                    "given": "Jane",
                    "family": "Smith",
                    "ORCID": "0000-0002-3456-7890",
                }
            ]
        }
        result = extract_author_details(publication)
        assert result[0]["ormolecule_id"] == "0000-0002-3456-7890"

    def test_extract_author_without_ormolecule_id(self) -> None:
        """Should handle author without ORCID."""
        publication = {"author": [{"given": "John", "family": "Doe"}]}
        result = extract_author_details(publication)
        assert result[0]["ormolecule_id"] is None
        assert result[0]["authenticated_ormolecule_id"] is None

    def test_extract_organization_author(self) -> None:
        """Should extract organization author with name field."""
        publication = {"author": [{"name": "World Health Organization"}]}
        result = extract_author_details(publication)
        assert len(result) == 1
        assert result[0]["given"] is None
        assert result[0]["family"] is None
        assert result[0]["name"] == "World Health Organization"

    def test_extract_multiple_affiliations(self) -> None:
        """Should extract multiple affiliations."""
        publication = {
            "author": [
                {
                    "given": "John",
                    "family": "Doe",
                    "affiliation": [
                        {"name": "University A"},
                        {"name": "University B"},
                    ],
                }
            ]
        }
        result = extract_author_details(publication)
        assert result[0]["affiliations"] == ["University A", "University B"]

    def test_extract_sequence_additional(self) -> None:
        """Should handle sequence='additional' value."""
        publication = {
            "author": [{"given": "John", "family": "Doe", "sequence": "additional"}]
        }
        result = extract_author_details(publication)
        assert result[0]["sequence"] == "additional"

    def test_invalid_sequence_ignored(self) -> None:
        """Should ignore invalid sequence values."""
        publication = {
            "author": [{"given": "John", "family": "Doe", "sequence": "unknown"}]
        }
        result = extract_author_details(publication)
        assert result[0]["sequence"] is None

    def test_empty_author_list(self) -> None:
        """Should return empty list for empty author list."""
        result = extract_author_details({"author": []})
        assert result == []

    def test_missing_author_key(self) -> None:
        """Should return empty list when author key missing."""
        result = extract_author_details({})
        assert result == []

    def test_skips_author_without_name(self) -> None:
        """Should skip authors with no identifiable name."""
        publication = {
            "author": [
                {"given": "", "family": ""},
                {"given": "Valid", "family": "Author"},
            ]
        }
        result = extract_author_details(publication)
        assert len(result) == 1
        assert result[0]["given"] == "Valid"

    def test_authenticated_ormolecule_id_false(self) -> None:
        """Should handle authenticated-ormolecule_id=False."""
        publication = {
            "author": [
                {
                    "given": "John",
                    "family": "Doe",
                    "ORCID": "0000-0001-2345-6789",
                    "authenticated-ormolecule_id": False,
                }
            ]
        }
        result = extract_author_details(publication)
        assert result[0]["authenticated_ormolecule_id"] is False

    def test_invalid_ormolecule_id_format_ignored(self) -> None:
        """Should return None for invalid ORCID format."""
        publication = {
            "author": [
                {"given": "John", "family": "Doe", "ORCID": "invalid-ormolecule_id"}
            ]
        }
        result = extract_author_details(publication)
        assert result[0]["ormolecule_id"] is None


class TestExtractAuthorOrcids:
    """Tests for extract_author_orcids function."""

    def test_extract_multiple_orcids(self) -> None:
        """Should extract ORCIDs from multiple authors."""
        publication = {
            "author": [
                {
                    "given": "John",
                    "family": "Doe",
                    "ORCID": "https://orcid.org/0000-0001-2345-6789",
                },
                {"given": "Jane", "family": "Smith"},
                {
                    "given": "Bob",
                    "family": "Wilson",
                    "ORCID": "0000-0002-3456-7890",
                },
            ]
        }
        result = extract_author_orcids(publication)
        assert result == ["0000-0001-2345-6789", "0000-0002-3456-7890"]

    def test_extract_single_orcid(self) -> None:
        """Should extract single ORCID."""
        publication = {
            "author": [
                {"given": "John", "family": "Doe", "ORCID": "0000-0001-2345-6789"}
            ]
        }
        result = extract_author_orcids(publication)
        assert result == ["0000-0001-2345-6789"]

    def test_no_orcids(self) -> None:
        """Should return empty list when no ORCIDs present."""
        publication = {
            "author": [
                {"given": "John", "family": "Doe"},
                {"given": "Jane", "family": "Smith"},
            ]
        }
        result = extract_author_orcids(publication)
        assert result == []

    def test_empty_publication(self) -> None:
        """Should return empty list for empty publication."""
        result = extract_author_orcids({})
        assert result == []

    def test_normalizes_url_prefix(self) -> None:
        """Should normalize ORCID URL to ID-only format."""
        publication = {
            "author": [
                {
                    "given": "John",
                    "family": "Doe",
                    "ORCID": "https://orcid.org/0000-0001-2345-6789",
                }
            ]
        }
        result = extract_author_orcids(publication)
        assert result == ["0000-0001-2345-6789"]

    def test_http_url_prefix(self) -> None:
        """Should handle legacy HTTP URL prefix."""
        publication = {
            "author": [
                {
                    "given": "John",
                    "family": "Doe",
                    "ORCID": LEGACY_HTTP_ORCID,
                }
            ]
        }
        result = extract_author_orcids(publication)
        assert result == ["0000-0001-2345-6789"]

    def test_invalid_orcid_excluded(self) -> None:
        """Should exclude invalid ORCIDs."""
        publication = {
            "author": [
                {"given": "John", "family": "Doe", "ORCID": "invalid"},
                {"given": "Jane", "family": "Smith", "ORCID": "0000-0001-2345-6789"},
            ]
        }
        result = extract_author_orcids(publication)
        assert result == ["0000-0001-2345-6789"]


class TestExtractReferences:
    """Tests for extract_references function."""

    def test_extract_complete_reference(self) -> None:
        """Should extract reference with all fields."""
        publication = {
            "reference": [
                {
                    "key": "ref1",
                    "DOI": "10.1000/xyz123",
                    "doi-asserted-by": "publisher",
                    "article-title": "Example Article",
                    "journal-title": "Nature",
                    "author": "Smith",
                    "year": "2020",
                    "volume": "42",
                    "issue": "3",
                    "first-page": "123",
                }
            ]
        }
        result = extract_references(publication)
        assert len(result) == 1
        ref = result[0]
        assert ref["key"] == "ref1"
        assert ref["doi"] == "10.1000/xyz123"
        assert ref["doi_asserted_by"] == "publisher"
        assert ref["article_title"] == "Example Article"
        assert ref["journal_title"] == "Nature"
        assert ref["author"] == "Smith"
        assert ref["year"] == 2020
        assert ref["volume"] == "42"
        assert ref["issue"] == "3"
        assert ref["first_page"] == "123"

    def test_extract_unstructured_reference(self) -> None:
        """Should extract unstructured citation string."""
        publication = {
            "reference": [
                {
                    "key": "ref1",
                    "unstructured": "Smith J. Example Article. Nature 2020;42:123.",
                }
            ]
        }
        result = extract_references(publication)
        assert (
            result[0]["unstructured"] == "Smith J. Example Article. Nature 2020;42:123."
        )

    def test_extract_book_reference(self) -> None:
        """Should extract book reference with volume-title."""
        publication = {
            "reference": [
                {
                    "key": "ref1",
                    "volume-title": "Biochemistry Textbook",
                    "author": "Berg",
                    "year": "2019",
                    "ISBN": "978-1-234567-89-0",
                }
            ]
        }
        result = extract_references(publication)
        ref = result[0]
        assert ref["volume_title"] == "Biochemistry Textbook"
        assert ref["isbn"] == "978-1-234567-89-0"

    def test_year_as_integer(self) -> None:
        """Should handle year as integer."""
        publication = {"reference": [{"key": "ref1", "year": 2020}]}
        result = extract_references(publication)
        assert result[0]["year"] == 2020

    def test_year_as_string(self) -> None:
        """Should convert year string to integer."""
        publication = {"reference": [{"key": "ref1", "year": "2020"}]}
        result = extract_references(publication)
        assert result[0]["year"] == 2020

    def test_invalid_year_ignored(self) -> None:
        """Should return None for non-numeric year."""
        publication = {"reference": [{"key": "ref1", "year": "unknown"}]}
        result = extract_references(publication)
        assert result[0]["year"] is None

    def test_doi_normalized_lowercase(self) -> None:
        """Should normalize DOI to lowercase."""
        publication = {"reference": [{"key": "ref1", "DOI": "10.1000/ABC123"}]}
        result = extract_references(publication)
        assert result[0]["doi"] == "10.1000/abc123"

    def test_empty_reference_list(self) -> None:
        """Should return empty list for empty references."""
        result = extract_references({"reference": []})
        assert result == []

    def test_missing_reference_key(self) -> None:
        """Should return empty list when reference key missing."""
        result = extract_references({})
        assert result == []

    def test_multiple_references(self) -> None:
        """Should extract multiple references preserving order."""
        publication = {
            "reference": [
                {"key": "ref1", "DOI": "10.1000/first"},
                {"key": "ref2", "DOI": "10.1000/second"},
            ]
        }
        result = extract_references(publication)
        assert len(result) == 2
        assert result[0]["key"] == "ref1"
        assert result[1]["key"] == "ref2"

    def test_series_title(self) -> None:
        """Should extract series-title for book series."""
        publication = {
            "reference": [{"key": "ref1", "series-title": "Methods in Enzymology"}]
        }
        result = extract_references(publication)
        assert result[0]["series_title"] == "Methods in Enzymology"

    def test_issn_extraction(self) -> None:
        """Should extract ISSN from reference."""
        publication = {"reference": [{"key": "ref1", "ISSN": "0028-0836"}]}
        result = extract_references(publication)
        assert result[0]["issn"] == "0028-0836"

    def test_extract_references__strips_whitespace__a25b8453(self) -> None:
        """Should strip whitespace from string fields."""
        publication = {
            "reference": [
                {
                    "key": "  ref1  ",
                    "article-title": "  Title  ",
                    "author": "  Smith  ",
                }
            ]
        }
        result = extract_references(publication)
        assert result[0]["key"] == "ref1"
        assert result[0]["article_title"] == "Title"
        assert result[0]["author"] == "Smith"

    def test_skips_non_dict_entries(self) -> None:
        """Should skip non-dict entries in reference array."""
        publication = {
            "reference": [
                "invalid",
                {"key": "ref1", "DOI": "10.1000/valid"},
            ]
        }
        result = extract_references(publication)
        assert len(result) == 1
        assert result[0]["key"] == "ref1"
