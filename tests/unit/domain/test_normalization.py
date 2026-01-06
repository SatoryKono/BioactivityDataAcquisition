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
