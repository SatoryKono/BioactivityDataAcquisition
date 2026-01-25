"""Unit tests for CrossRef field extractors.

Tests the pure functions in extractors.py module.
"""

from __future__ import annotations

import pytest

from bioetl.application.pipelines.crossref.extractors import (
    extract_authors,
    extract_content_domain,
    extract_dates,
    extract_issn_by_type,
    extract_journal_info,
    extract_license_url,
    extract_page_info,
    extract_published_date,
    extract_year,
)


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

    def test_extract_authors_empty_list(self) -> None:
        """Should return empty list for empty author list."""
        publication = {"author": []}
        result = extract_authors(publication)
        assert result == []

    def test_extract_authors_missing_key(self) -> None:
        """Should return empty list when author key is missing."""
        publication = {}
        result = extract_authors(publication)
        assert result == []

    def test_extract_authors_strips_whitespace(self) -> None:
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


class TestExtractYear:
    """Tests for extract_year function."""

    def test_extract_year_from_published_print(self) -> None:
        """Should extract year from published-print field."""
        publication = {"published-print": {"date-parts": [[2023, 6, 15]]}}
        result = extract_year(publication)
        assert result == 2023

    def test_extract_year_from_published_online(self) -> None:
        """Should fall back to published-online field."""
        publication = {"published-online": {"date-parts": [[2022, 3, 1]]}}
        result = extract_year(publication)
        assert result == 2022

    def test_extract_year_from_issued(self) -> None:
        """Should fall back to issued field."""
        publication = {"issued": {"date-parts": [[2021, 1, 1]]}}
        result = extract_year(publication)
        assert result == 2021

    def test_extract_year_priority_order(self) -> None:
        """Should prefer published-print over other date fields."""
        publication = {
            "published-print": {"date-parts": [[2023, 6, 1]]},
            "published-online": {"date-parts": [[2023, 5, 1]]},
            "issued": {"date-parts": [[2023, 4, 1]]},
        }
        result = extract_year(publication)
        assert result == 2023

    def test_extract_year_year_only(self) -> None:
        """Should extract year from date-parts with only year."""
        publication = {"published-print": {"date-parts": [[2020]]}}
        result = extract_year(publication)
        assert result == 2020

    def test_extract_year_empty_dict(self) -> None:
        """Should return None for empty publication dict."""
        result = extract_year({})
        assert result is None

    def test_extract_year_empty_date_parts(self) -> None:
        """Should return None for empty date-parts."""
        publication = {"published-print": {"date-parts": [[]]}}
        result = extract_year(publication)
        assert result is None

    def test_extract_year_non_integer(self) -> None:
        """Should return None for non-integer year."""
        publication = {"published-print": {"date-parts": [["2023"]]}}
        result = extract_year(publication)
        assert result is None

    def test_extract_year_out_of_range_low(self) -> None:
        """Should return None for year below valid range (1800)."""
        publication = {"published-print": {"date-parts": [[1799]]}}
        result = extract_year(publication)
        assert result is None

    def test_extract_year_out_of_range_high(self) -> None:
        """Should return None for year above valid range (2100)."""
        publication = {"published-print": {"date-parts": [[2101]]}}
        result = extract_year(publication)
        assert result is None

    def test_extract_year_valid_boundary_low(self) -> None:
        """Should accept year at lower boundary (1800)."""
        publication = {"published-print": {"date-parts": [[1800]]}}
        result = extract_year(publication)
        assert result == 1800

    def test_extract_year_valid_boundary_high(self) -> None:
        """Should accept year at upper boundary (2100)."""
        publication = {"published-print": {"date-parts": [[2100]]}}
        result = extract_year(publication)
        assert result == 2100


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

    def test_extract_license_url_empty_list(self) -> None:
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
            "issn": ["0028-0836", "1476-4687"],
            "publisher": "Springer Nature",
        }

    def test_extract_journal_info_partial(self) -> None:
        """Should handle missing fields gracefully."""
        publication = {"container-title": ["Nature"]}
        result = extract_journal_info(publication)
        assert result["journal"] == "Nature"
        assert result["issn"] == []
        assert result["publisher"] is None

    def test_extract_journal_info_empty(self) -> None:
        """Should return defaults for empty publication."""
        result = extract_journal_info({})
        assert result == {"journal": None, "issn": [], "publisher": None}

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
            "first_page": "123",
            "last_page": "145",
        }

    def test_extract_page_info_single_page(self) -> None:
        """Should handle single page number."""
        publication = {"page": "42"}
        result = extract_page_info(publication)
        assert result["first_page"] == "42"
        assert result["last_page"] is None

    def test_extract_page_info_missing_fields(self) -> None:
        """Should return None for missing fields."""
        result = extract_page_info({})
        assert result == {
            "volume": None,
            "issue": None,
            "first_page": None,
            "last_page": None,
        }

    def test_extract_page_info_partial(self) -> None:
        """Should handle partial page info."""
        publication = {"volume": "10", "page": "1-50"}
        result = extract_page_info(publication)
        assert result["volume"] == "10"
        assert result["issue"] is None
        assert result["first_page"] == "1"
        assert result["last_page"] == "50"

    def test_extract_page_info_article_number(self) -> None:
        """Should handle article numbers (e-pages)."""
        publication = {"page": "e12345"}
        result = extract_page_info(publication)
        assert result["first_page"] == "e12345"
        assert result["last_page"] is None


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
    def test_extract_issn_by_type(
        self, input_data: dict, expected: dict
    ) -> None:
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

    def test_empty_record(self) -> None:
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
