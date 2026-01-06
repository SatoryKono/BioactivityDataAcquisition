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
    normalize_string,
    normalize_to_string,
    parse_authors_to_list,
    parse_date_field,
    parse_page_range,
    strip_html_tags,
)


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


class TestNormalizeDoi:
    """Tests for normalize_doi function."""

    @pytest.mark.parametrize(
        "doi,expected",
        [
            ("10.1038/nature12373", "10.1038/nature12373"),
            ("10.1038/NATURE12373", "10.1038/nature12373"),
            ("  10.1038/nature12373  ", "10.1038/nature12373"),
            ("  10.1038/NATURE12373  ", "10.1038/nature12373"),
            (None, None),
        ],
    )
    def test_normalize_doi(self, doi: str | None, expected: str | None) -> None:
        """Test DOI normalization."""
        assert normalize_doi(doi) == expected


class TestFormatDateParts:
    """Tests for format_date_parts function."""

    @pytest.mark.parametrize(
        "date_parts,expected",
        [
            ([[2024, 3, 15]], "2024-03-15"),
            ([[2024, 3]], "2024-03"),
            ([[2024]], "2024"),
            ([[2024, 1, 5]], "2024-01-05"),
            ([[2024, 12, 31]], "2024-12-31"),
            (None, None),
            ([], None),
            ([[]], None),
        ],
    )
    def test_format_date_parts(
        self, date_parts: list[list[int]] | None, expected: str | None
    ) -> None:
        """Test date-parts formatting."""
        assert format_date_parts(date_parts) == expected


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
            ("<p>Hello world</p>", "Hello world"),
            ("<b>Bold</b> text", "Bold text"),
            ("<jats:p>Abstract text</jats:p>", "Abstract text"),
            ("Plain text", "Plain text"),
            ("  <p>Spaced</p>  ", "Spaced"),
            ("", None),
            (None, None),
            ("<p></p>", None),  # Empty after stripping
        ],
    )
    def test_strip_html_tags(self, text: str | None, expected: str | None) -> None:
        """Test HTML tag stripping."""
        assert strip_html_tags(text) == expected

    def test_nested_tags(self) -> None:
        """Test stripping nested HTML tags."""
        assert strip_html_tags("<div><p>Nested <b>tags</b></p></div>") == "Nested tags"


class TestParsePageRange:
    """Tests for parse_page_range function."""

    @pytest.mark.parametrize(
        "page,expected",
        [
            ("123-456", ("123", "456")),
            ("123", ("123", None)),
            ("123-", ("123", None)),
            ("-456", (None, "456")),
            ("  123  -  456  ", ("123", "456")),
            ("", (None, None)),
            (None, (None, None)),
        ],
    )
    def test_parse_page_range(
        self, page: str | None, expected: tuple[str | None, str | None]
    ) -> None:
        """Test page range parsing."""
        assert parse_page_range(page) == expected


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
