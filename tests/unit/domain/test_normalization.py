"""Tests for domain.normalization module.

Tests pure normalization functions per REFACTOR-004.
"""

from __future__ import annotations

from datetime import date

import pytest

from bioetl.domain.normalization import (
    extract_first_item,
    extract_first_string,
    format_date_parts,
    normalize_doi,
    normalize_partial_date,
    normalize_pmc_id,
    normalize_pmid,
    normalize_string,
    normalize_to_string,
    parse_authors_to_list,
    parse_date_field,
    parse_page_range,
    strip_doi_prefix,
    strip_html_tags,
    validate_publication_year,
)

LEGACY_HTTP_DOI = "http" + "://doi.org/10.1016/j.cell.2024"


class TestNormalizeString:
    """Tests for normalize_string function."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("hello", "hello"),
            ("  hello  ", "hello"),
            ("hello world", "hello world"),
            ("  ", None),
            ("", None),
            (None, None),
        ],
    )
    def test_normalize_string(self, value: str | None, expected: str | None) -> None:
        """Test string normalization."""
        assert normalize_string(value) == expected


class TestNormalizeToString:
    """Tests for normalize_to_string function."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("hello", "hello"),
            ("  hello  ", "hello"),
            (42, "42"),
            (3.14, "3.14"),
            (True, "True"),
            ("", None),
            ("  ", None),
            (None, None),
        ],
    )
    def test_normalize_to_string(self, value, expected: str | None) -> None:
        """Test conversion and normalization to string."""
        assert normalize_to_string(value) == expected


class TestStripDoiPrefix:
    """Tests for strip_doi_prefix function."""

    @pytest.mark.parametrize(
        "doi,expected",
        [
            ("https://doi.org/10.1038/nature12373", "10.1038/nature12373"),
            (LEGACY_HTTP_DOI, "10.1016/j.cell.2024"),
            ("doi:10.1126/science.abc1234", "10.1126/science.abc1234"),
            ("DOI:10.1001/jama.2024.0001", "10.1001/jama.2024.0001"),
            ("10.1038/nature12373", "10.1038/nature12373"),
            ("not-a-doi-prefix/10.1038/test", "not-a-doi-prefix/10.1038/test"),
        ],
    )
    def test_strip_doi_prefix(self, doi: str, expected: str) -> None:
        """Test DOI prefix stripping for all supported prefix formats."""
        assert strip_doi_prefix(doi) == expected

    def test_strip_doi_prefix_preserves_case(self) -> None:
        """Prefix stripping should NOT change DOI case."""
        assert strip_doi_prefix("https://doi.org/10.1038/NATURE") == "10.1038/NATURE"


class TestNormalizeDoi:
    """Tests for normalize_doi function."""

    @pytest.mark.parametrize(
        "doi,expected",
        [
            ("10.1038/nature12373", "10.1038/nature12373"),
            ("10.1038/NATURE12373", "10.1038/nature12373"),
            ("  10.1038/nature12373  ", "10.1038/nature12373"),
            ("  10.1038/NATURE12373  ", "10.1038/nature12373"),
            ("https://doi.org/10.1038/NATURE12373", "10.1038/nature12373"),
            (" HTTPS://doi.org/10.1038/NATURE12373 ", "10.1038/nature12373"),
            ("doi:10.1126/SCIENCE.ABC1234", "10.1126/science.abc1234"),
            (None, None),
        ],
    )
    def test_normalize_doi(self, doi: str | None, expected: str | None) -> None:
        """Test DOI normalization."""
        assert normalize_doi(doi) == expected


class TestFormatDateParts:
    """Tests for format_date_parts function.

    Uses end-of-period normalization:
    - Complete dates stay as-is
    - Month-only dates use last day of month
    - Year-only dates use December 31st
    """

    @pytest.mark.parametrize(
        "date_parts,expected",
        [
            # Complete dates (no normalization needed)
            ([[2024, 3, 15]], "2024-03-15"),
            ([[2024, 1, 5]], "2024-01-05"),
            ([[2024, 12, 31]], "2024-12-31"),
            # Month-only: end-of-period (last day of month)
            ([[2024, 3]], "2024-03-31"),  # March has 31 days
            ([[2024, 2]], "2024-02-29"),  # 2024 is leap year
            ([[2023, 2]], "2023-02-28"),  # 2023 is not leap year
            ([[2024, 4]], "2024-04-30"),  # April has 30 days
            ([[2024, 1]], "2024-01-31"),  # January has 31 days
            # Year-only: end-of-period (December 31st)
            ([[2024]], "2024-12-31"),
            ([[2023]], "2023-12-31"),
            # Edge cases
            (None, None),
            ([], None),
            ([[]], None),
        ],
    )
    def test_format_date_parts(
        self, date_parts: list[list[int]] | None, expected: str | None
    ) -> None:
        """Test date-parts formatting with end-of-period normalization."""
        assert format_date_parts(date_parts) == expected

    def test_format_date_parts_leap_year(self) -> None:
        """Test February end-of-period for leap vs non-leap years."""
        # Leap years: divisible by 4, except centuries not divisible by 400
        assert format_date_parts([[2000, 2]]) == "2000-02-29"  # Divisible by 400
        assert format_date_parts([[1900, 2]]) == "1900-02-28"  # Century, not div by 400
        assert format_date_parts([[2020, 2]]) == "2020-02-29"  # Leap year
        assert format_date_parts([[2021, 2]]) == "2021-02-28"  # Not leap year


class TestNormalizePmid:
    """Tests for normalize_pmid function."""

    @pytest.mark.parametrize(
        "pmid,expected",
        [
            (12345678, "12345678"),
            ("12345678", "12345678"),
            ("  12345678  ", "12345678"),
            ("012345678", "12345678"),
            ("9999999999", "9999999999"),
            (None, None),
            ("", None),
            ("abc", None),
            ("12.34", None),
            (0, None),
            (-1, None),
            (10_000_000_000, None),
            ("10000000000", None),
            (True, None),
            (False, None),
        ],
    )
    def test_normalize_pmid(self, pmid: str | int | None, expected: str | None) -> None:
        """Test PMID normalization."""
        assert normalize_pmid(pmid) == expected


class TestNormalizePartialDate:
    """Tests for normalize_partial_date function."""

    @pytest.mark.parametrize(
        "date_str,expected",
        [
            ("2024-03-15", "2024-03-15"),
            ("2024-03", "2024-03-31"),
            ("2024-02", "2024-02-29"),
            ("2023-02", "2023-02-28"),
            ("2024", "2024-12-31"),
            ("  2024-03  ", "2024-03-31"),
            ("2024/03", None),
            (None, None),
        ],
    )
    def test_normalize_partial_date(
        self, date_str: str | None, expected: str | None
    ) -> None:
        """Test canonical partial-date normalization."""
        assert normalize_partial_date(date_str) == expected


class TestValidatePublicationYear:
    """Tests for validate_publication_year function."""

    @pytest.mark.parametrize(
        ("year", "min_year", "max_year", "expected"),
        [
            (2024, 1500, 2100, (2024, False)),
            (1500, 1500, 2100, (1500, False)),
            (2100, 1500, 2100, (2100, False)),
            (1499, 1500, 2100, (1499, True)),
            (2101, 1500, 2100, (2101, True)),
            (None, 1500, 2100, (None, False)),
        ],
    )
    def test_validate_publication_year(
        self,
        year: int | None,
        min_year: int,
        max_year: int,
        expected: tuple[int | None, bool],
    ) -> None:
        """Year validation should be deterministic for explicit bounds."""
        assert (
            validate_publication_year(
                year,
                min_year=min_year,
                max_year=max_year,
            )
            == expected
        )


class TestParseDateField:
    """Tests for parse_date_field function."""

    def test_valid_iso_date(self) -> None:
        """Test parsing ISO date."""
        assert parse_date_field("2024-03-15") == date(2024, 3, 15)

    def test_valid_date_with_whitespace(self) -> None:
        """Test parsing date with whitespace."""
        assert parse_date_field("  2024-03-15  ") == date(2024, 3, 15)

    def test_custom_format(self) -> None:
        """Test parsing with custom format."""
        assert parse_date_field("15/03/2024", "%d/%m/%Y") == date(2024, 3, 15)

    @pytest.mark.parametrize(
        "value",
        [
            "invalid",
            "2024-13-01",  # Invalid month
            "2024-01-32",  # Invalid day
            "",
            None,
        ],
    )
    def test_invalid_date(self, value: str | None) -> None:
        """Test invalid dates return None."""
        assert parse_date_field(value) is None


class TestStripHtmlTags:
    """Tests for strip_html_tags function."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            # Basic HTML tags
            ("<p>Hello world</p>", "Hello world"),
            ("<b>Bold</b> text", "Bold text"),
            ("<jats:p>Abstract text</jats:p>", "Abstract text"),
            ("Plain text", "Plain text"),
            ("  <p>Spaced</p>  ", "Spaced"),
            ("", None),
            (None, None),
            ("<p></p>", None),  # Empty after stripping
            # HTML entity decoding
            ("&amp; &lt; &gt;", "& < >"),
            ("5 &gt; 3 &amp;&amp; 2 &lt; 4", "5 > 3 && 2 < 4"),
            ("H&auml;llo W&ouml;rld", "Hällo Wörld"),
            ("&quot;quoted&quot;", '"quoted"'),
            ("&apos;apostrophe&apos;", "'apostrophe'"),
            # Note: &nbsp; is decoded to \xa0 but our whitespace normalization
            # treats \xa0 as whitespace and collapses it
            ("&nbsp;non-breaking&nbsp;space", "non-breaking space"),
            # Whitespace normalization
            ("  Multiple   spaces  ", "Multiple spaces"),
            ("Line\nbreak", "Line break"),
            ("Tab\there", "Tab here"),
            ("Mixed\n\t  spaces", "Mixed spaces"),
            # Tags between content don't add spaces
            ("<p>Para 1</p><p>Para 2</p>", "Para 1Para 2"),
            # But newlines between tags are normalized to spaces
            ("<p>Para 1</p>\n\n<p>Para 2</p>", "Para 1 Para 2"),
            # XSS script tags
            ("<script>alert('xss')</script>Text", "alert('xss')Text"),
            ("<SCRIPT>malicious</SCRIPT>Safe", "maliciousSafe"),
            # Combined scenarios
            ("<p>&amp; test &lt;value&gt;</p>", "& test <value>"),
            (
                "<jats:p>  Multiple &amp; spaces  </jats:p>",
                "Multiple & spaces",
            ),
        ],
    )
    def test_strip_html_tags(self, text: str | None, expected: str | None) -> None:
        """Test HTML tag stripping with entity decoding and whitespace normalization."""
        assert strip_html_tags(text) == expected

    def test_nested_tags(self) -> None:
        """Test stripping nested HTML tags."""
        assert strip_html_tags("<div><p>Nested <b>tags</b></p></div>") == "Nested tags"

    def test_complex_html_abstract(self) -> None:
        """Test stripping complex HTML typical in scientific abstracts."""
        html = """<jats:p>This study investigates the &alpha;-receptor
        binding affinity of <jats:italic>compound X</jats:italic>.
        Results show IC<jats:sub>50</jats:sub> &lt; 10 nM.</jats:p>"""
        expected = (
            "This study investigates the \u03b1-receptor binding affinity of compound X. "
            "Results show IC50 < 10 nM."
        )
        assert strip_html_tags(html) == expected

    def test_script_tag_content_preserved(self) -> None:
        """Test that script tag content is preserved (tags removed, content kept).

        Note: This function only strips tags, it doesn't sanitize for security.
        Security-sensitive contexts should use proper HTML sanitization libraries.
        """
        result = strip_html_tags("<script>alert(1)</script>Safe text")
        assert result == "alert(1)Safe text"

    def test_numeric_entities(self) -> None:
        """Test decoding of numeric HTML entities."""
        assert strip_html_tags("&#60;tag&#62;") == "<tag>"
        assert strip_html_tags("&#x3C;hex&#x3E;") == "<hex>"


class TestParsePageRange:
    """Tests for parse_page_range function."""

    @pytest.mark.parametrize(
        "page,expected",
        [
            # Standard ranges
            ("123-456", ("123", "456")),
            ("1-999", ("1", "999")),
            # Single pages
            ("123", ("123", None)),
            ("100234", ("100234", None)),
            # Trailing/leading hyphen
            ("123-", ("123", None)),
            ("-456", (None, None)),
            # Whitespace handling
            ("  123  -  456  ", ("123", "456")),
            # Empty/None
            ("", (None, None)),
            (None, (None, None)),
            # Supplements (should split - these are actual ranges)
            ("S1-S15", ("S1", "S15")),
            ("A1-A10", ("A1", "A10")),
        ],
    )
    def test_parse_page_range(
        self, page: str | None, expected: tuple[str | None, str | None]
    ) -> None:
        """Test page range parsing."""
        assert parse_page_range(page) == expected


class TestParsePageRangeAbbreviated:
    """Tests for abbreviated page range expansion in parse_page_range.

    Academic publishing often abbreviates page ranges:
    - "737-9" means 737-739 (not 737-9)
    - "737-39" means 737-739
    - "199-3" means 199-203 (rollover case)
    """

    @pytest.mark.parametrize(
        "page,expected",
        [
            # Abbreviated single digit
            ("737-9", ("737", "739")),
            # Abbreviated two digits
            ("737-39", ("737", "739")),
            # Full range (no expansion)
            ("737-839", ("737", "839")),
            # Full range same digit count
            ("123-145", ("123", "145")),
            # Rollover case
            ("199-3", ("199", "203")),
            # Four-digit abbreviation
            ("1234-56", ("1234", "1256")),
            # En-dash (U+2013)
            ("737\u20139", ("737", "739")),
            # Em-dash (U+2014)
            ("737\u20149", ("737", "739")),
            # Whitespace with abbreviation
            ("\n  737-9\n  ", ("737", "739")),
            ("737 - 9", ("737", "739")),
        ],
    )
    def test_abbreviated_page_expansion(
        self, page: str, expected: tuple[str | None, str | None]
    ) -> None:
        """Test abbreviated page range expansion."""
        assert parse_page_range(page) == expected


class TestParsePageRangeElectronic:
    """Tests for electronic pagination handling in parse_page_range.

    Electronic article identifiers like 'e-123' or 'e123' should NOT be split
    on hyphen - the hyphen is part of the identifier, not a range separator.
    """

    @pytest.mark.parametrize(
        "page,expected",
        [
            # Electronic pages with hyphen (should NOT split)
            ("e-123", ("e-123", None)),
            ("E-456", ("E-456", None)),
            ("e-1", ("e-1", None)),
            ("E-99999", ("E-99999", None)),
            # Electronic pages without hyphen
            ("e12345", ("e12345", None)),
            ("E789", ("E789", None)),
            # Not electronic pages (should still split)
            ("e100-e200", ("e100", "e200")),  # Range of electronic pages
            ("ex-123", ("ex", "123")),  # Not matching pattern
        ],
    )
    def test_electronic_pagination(
        self, page: str, expected: tuple[str | None, str | None]
    ) -> None:
        """Test electronic page identifiers are not split incorrectly."""
        assert parse_page_range(page) == expected


class TestNormalizePmcId:
    """Tests for normalize_pmc_id function."""

    @pytest.mark.parametrize(
        "pmc_id,expected",
        [
            # Already has prefix - uppercase
            ("PMC1234567", "PMC1234567"),
            # Lowercase prefix - normalizes to uppercase
            ("pmc1234567", "PMC1234567"),
            # Mixed case prefix
            ("Pmc1234567", "PMC1234567"),
            # No prefix - adds PMC prefix
            ("1234567", "PMC1234567"),
            # With whitespace
            ("  PMC1234567  ", "PMC1234567"),
            ("  1234567  ", "PMC1234567"),
            # Empty values
            (None, None),
            ("", None),
            ("   ", None),
        ],
    )
    def test_normalize_pmc_id(self, pmc_id: str | None, expected: str | None) -> None:
        """Test PMC ID normalization."""
        assert normalize_pmc_id(pmc_id) == expected


class TestExtractFirstItem:
    """Tests for extract_first_item function."""

    @pytest.mark.parametrize(
        "items,expected",
        [
            (["a", "b", "c"], "a"),
            ([1, 2, 3], 1),
            ([None, "b"], "b"),
            (["single"], "single"),
            ([], None),
            (None, None),
        ],
    )
    def test_extract_first_item(self, items, expected) -> None:
        """Test first item extraction."""
        assert extract_first_item(items) == expected


class TestExtractFirstString:
    """Tests for extract_first_string function."""

    @pytest.mark.parametrize(
        "items,expected",
        [
            (["  hello  ", "world"], "hello"),
            (["title", "subtitle"], "title"),
            ([None, "fallback"], "fallback"),
            ([], None),
            (None, None),
            (["", "fallback"], "fallback"),  # Empty string skipped
        ],
    )
    def test_extract_first_string(
        self, items: list[str] | None, expected: str | None
    ) -> None:
        """Test first string extraction with normalization."""
        assert extract_first_string(items) == expected


class TestParseAuthorsToList:
    """Tests for parse_authors_to_list function.

    This function parses various author input formats into a unified list:
    - Direct list[str]: Passed through with whitespace stripping
    - JSON string: Parsed as JSON array
    - Concatenated string: Split by semicolon or comma delimiters
    """

    @pytest.mark.parametrize(
        "input_authors,expected",
        [
            # Direct list input
            (["John Doe", "Jane Smith"], ["John Doe", "Jane Smith"]),
            (["  John Doe  ", "  Jane Smith  "], ["John Doe", "Jane Smith"]),
            (["Single Author"], ["Single Author"]),
            ([], []),
            # JSON string input
            ('["John Doe", "Jane Smith"]', ["John Doe", "Jane Smith"]),
            ('["Single Author"]', ["Single Author"]),
            ("[]", []),
            # Semicolon-separated (ChEMBL format)
            ("John Doe; Jane Smith", ["John Doe", "Jane Smith"]),
            ("  John Doe  ;  Jane Smith  ", ["John Doe", "Jane Smith"]),
            ("John Doe;Jane Smith;Bob Jones", ["John Doe", "Jane Smith", "Bob Jones"]),
            # Comma-separated
            ("John Doe, Jane Smith", ["John Doe", "Jane Smith"]),
            ("  John Doe  ,  Jane Smith  ", ["John Doe", "Jane Smith"]),
            # Single author (no delimiter)
            ("John Doe", ["John Doe"]),
            ("  John Doe  ", ["John Doe"]),
            # None and empty
            (None, []),
            ("", []),
            ("   ", []),
        ],
    )
    def test_parse_authors_to_list(
        self, input_authors: list[str] | str | None, expected: list[str]
    ) -> None:
        """Test parsing various author input formats."""
        assert parse_authors_to_list(input_authors) == expected

    def test_parse_authors_filters_empty_strings(self) -> None:
        """Test that empty strings are filtered from the result."""
        assert parse_authors_to_list(["John Doe", "", "Jane Smith"]) == [
            "John Doe",
            "Jane Smith",
        ]
        assert parse_authors_to_list("John Doe;;Jane Smith") == [
            "John Doe",
            "Jane Smith",
        ]

    def test_parse_authors_json_with_null(self) -> None:
        """Test parsing JSON array with null values."""
        assert parse_authors_to_list('["John Doe", null, "Jane Smith"]') == [
            "John Doe",
            "Jane Smith",
        ]

    def test_parse_authors_prefers_semicolon_over_comma(self) -> None:
        """Test that semicolon takes precedence over comma as delimiter.

        This is important for names with commas like "Doe, John".
        ChEMBL uses semicolon-separated format.
        """
        # When both semicolon and comma are present, semicolon wins
        result = parse_authors_to_list("Doe, John; Smith, Jane")
        assert result == ["Doe, John", "Smith, Jane"]

    def test_parse_authors_with_count(self) -> None:
        """Test that parsed list has expected count."""
        # List input
        result = parse_authors_to_list(["Smith J", "Jones A"])
        assert len(result) == 2

        # JSON string
        result = parse_authors_to_list('["Smith J", "Jones A"]')
        assert len(result) == 2

        # Concatenated string
        result = parse_authors_to_list("Smith J; Jones A")
        assert len(result) == 2

    def test_parse_authors_malformed_json_fallback(self) -> None:
        """Test that malformed JSON falls back to delimiter parsing."""
        # Starts with '[' but is not valid JSON - should fall back to delimiter
        result = parse_authors_to_list("[John Doe; Jane Smith")
        # Falls back to semicolon parsing after JSON fails
        assert result == ["[John Doe", "Jane Smith"]

    def test_parse_authors_non_string_items_in_list(self) -> None:
        """Test handling of non-string items in list input."""
        # Non-string items should be filtered out
        result = parse_authors_to_list(["John Doe", 123, None, "Jane Smith"])  # type: ignore[list-item]
        assert result == ["John Doe", "Jane Smith"]

    def test_parse_authors_unicode(self) -> None:
        """Test handling of unicode characters in author names."""
        result = parse_authors_to_list(["José García", "François Müller"])
        assert result == ["José García", "François Müller"]

        result = parse_authors_to_list("José García; François Müller")
        assert result == ["José García", "François Müller"]

    def test_parse_authors_json_unicode(self) -> None:
        """Test handling of JSON with unicode characters."""
        result = parse_authors_to_list('["José García", "François Müller"]')
        assert result == ["José García", "François Müller"]
