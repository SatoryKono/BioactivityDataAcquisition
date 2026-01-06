"""Tests for DefaultDataNormalizationService.

Tests the unified data normalization service for text and publication metadata.
"""

from __future__ import annotations

import json

import pytest

from bioetl.domain.services import (
    DataNormalizationConfig,
    DataNormalizationService,
    DefaultDataNormalizationService,
)


class TestDefaultDataNormalizationServiceInit:
    """Tests for service initialization."""

    def test_default_config(self) -> None:
        """Test service initializes with default config."""
        service = DefaultDataNormalizationService()
        assert service.config.min_publication_year == 1800
        assert service.config.max_publication_year == 2100

    def test_custom_config(self) -> None:
        """Test service accepts custom config."""
        config = DataNormalizationConfig(min_publication_year=1900)
        service = DefaultDataNormalizationService(config=config)
        assert service.config.min_publication_year == 1900

    def test_alias_works(self) -> None:
        """Test DataNormalizationService alias works."""
        service = DataNormalizationService()
        assert isinstance(service, DefaultDataNormalizationService)


class TestNormalizeDoi:
    """Tests for normalize_doi method."""

    @pytest.mark.parametrize(
        "doi,expected",
        [
            ("10.1038/nature12373", "10.1038/nature12373"),
            ("10.1038/NATURE12373", "10.1038/nature12373"),
            ("  10.1038/nature12373  ", "10.1038/nature12373"),
            ("  10.1038/NATURE12373  ", "10.1038/nature12373"),
            (None, None),
            ("", None),
        ],
    )
    def test_normalize_doi(self, doi: str | None, expected: str | None) -> None:
        """Test DOI normalization."""
        service = DefaultDataNormalizationService()
        assert service.normalize_doi(doi) == expected


class TestNormalizePmid:
    """Tests for normalize_pmid method."""

    @pytest.mark.parametrize(
        "pmid,expected",
        [
            (12345678, "12345678"),
            ("12345678", "12345678"),
            ("  12345678  ", "12345678"),
            ("012345678", "12345678"),  # Leading zeros removed
            (None, None),
            ("", None),
            ("abc", None),
            ("12.34", None),
            (0, None),
            (-1, None),
            (True, None),  # Booleans rejected
            (False, None),
        ],
    )
    def test_normalize_pmid(self, pmid: str | int | None, expected: str | None) -> None:
        """Test PMID normalization."""
        service = DefaultDataNormalizationService()
        assert service.normalize_pmid(pmid) == expected


class TestNormalizeYear:
    """Tests for normalize_year method."""

    @pytest.mark.parametrize(
        "year,expected_year,expected_warning",
        [
            (2024, 2024, False),
            (1800, 1800, False),
            (2100, 2100, False),
            (1799, 1799, True),
            (2101, 2101, True),
            (1500, 1500, True),
            (None, None, False),
        ],
    )
    def test_normalize_year(
        self, year: int | None, expected_year: int | None, expected_warning: bool
    ) -> None:
        """Test year normalization with default config."""
        service = DefaultDataNormalizationService()
        result_year, result_warning = service.normalize_year(year)
        assert result_year == expected_year
        assert result_warning == expected_warning

    def test_normalize_year_custom_range(self) -> None:
        """Test year normalization with custom range."""
        config = DataNormalizationConfig(
            min_publication_year=1900, max_publication_year=2050
        )
        service = DefaultDataNormalizationService(config=config)

        # 1899 should be flagged as warning with custom range
        year, warning = service.normalize_year(1899)
        assert year == 1899
        assert warning is True

        # 1900 should be valid
        year, warning = service.normalize_year(1900)
        assert year == 1900
        assert warning is False


class TestNormalizeAuthors:
    """Tests for normalize_authors method."""

    def test_normalize_authors_list(self) -> None:
        """Test hashing list of authors."""
        service = DefaultDataNormalizationService()
        result = service.normalize_authors(["John Doe", "Jane Smith"], salt="test_salt")

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2
        # Hashes should be consistent
        expected_hash_john = service._hash_pii("John Doe", "test_salt")
        assert parsed[0] == expected_hash_john

    def test_normalize_authors_string(self) -> None:
        """Test hashing semicolon-separated authors."""
        service = DefaultDataNormalizationService()
        result = service.normalize_authors("John Doe; Jane Smith", salt="test_salt")

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_normalize_authors_json_string(self) -> None:
        """Test hashing JSON-serialized authors."""
        service = DefaultDataNormalizationService()
        result = service.normalize_authors(
            '["John Doe", "Jane Smith"]', salt="test_salt"
        )

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_normalize_authors_empty(self) -> None:
        """Test empty authors returns None."""
        service = DefaultDataNormalizationService()
        assert service.normalize_authors(None, salt="test_salt") is None
        assert service.normalize_authors([], salt="test_salt") is None
        assert service.normalize_authors("", salt="test_salt") is None


class TestStripHtmlTags:
    """Tests for strip_html_tags method."""

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
            ("<p></p>", None),
            # HTML entity decoding
            ("&amp; &lt; &gt;", "& < >"),
            ("5 &gt; 3 &amp;&amp; 2 &lt; 4", "5 > 3 && 2 < 4"),
            ("H&auml;llo W&ouml;rld", "Hällo Wörld"),
            # Whitespace normalization
            ("  Multiple   spaces  ", "Multiple spaces"),
            ("Line\nbreak", "Line break"),
        ],
    )
    def test_strip_html_tags(self, text: str | None, expected: str | None) -> None:
        """Test HTML tag stripping with entity decoding."""
        service = DefaultDataNormalizationService()
        assert service.strip_html_tags(text) == expected


class TestNormalizeOaStatus:
    """Tests for normalize_oa_status method."""

    @pytest.mark.parametrize(
        "status,expected",
        [
            ("GOLD", "gold"),
            ("Gold", "gold"),
            ("gold", "gold"),
            ("GREEN", "green"),
            ("bronze", "bronze"),
            ("hybrid", "hybrid"),
            ("closed", "closed"),
            ("  GOLD  ", "gold"),
            (None, None),
            ("", None),
            ("   ", None),
        ],
    )
    def test_normalize_oa_status(
        self, status: str | None, expected: str | None
    ) -> None:
        """Test OA status normalization."""
        service = DefaultDataNormalizationService()
        assert service.normalize_oa_status(status) == expected


class TestNormalizeString:
    """Tests for normalize_string method."""

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
        service = DefaultDataNormalizationService()
        assert service.normalize_string(value) == expected


class TestParseAuthorsToList:
    """Tests for parse_authors_to_list method."""

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
            # Comma-separated
            ("John Doe, Jane Smith", ["John Doe", "Jane Smith"]),
            # Single author
            ("John Doe", ["John Doe"]),
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
        service = DefaultDataNormalizationService()
        assert service.parse_authors_to_list(input_authors) == expected

    def test_parse_authors_semicolon_preference(self) -> None:
        """Test that semicolon takes precedence over comma as delimiter."""
        service = DefaultDataNormalizationService()
        # When both semicolon and comma are present, semicolon wins
        result = service.parse_authors_to_list("Doe, John; Smith, Jane")
        assert result == ["Doe, John", "Smith, Jane"]


class TestFormatDateParts:
    """Tests for format_date_parts method."""

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
        service = DefaultDataNormalizationService()
        assert service.format_date_parts(date_parts) == expected


class TestDataNormalizationConfig:
    """Tests for DataNormalizationConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = DataNormalizationConfig()
        assert config.min_publication_year == 1800
        assert config.max_publication_year == 2100
        assert config.default_pii_salt == ""

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = DataNormalizationConfig(
            min_publication_year=1900,
            max_publication_year=2050,
            default_pii_salt="my_salt",
        )
        assert config.min_publication_year == 1900
        assert config.max_publication_year == 2050
        assert config.default_pii_salt == "my_salt"

    def test_invalid_year_range(self) -> None:
        """Test validation of year range."""
        with pytest.raises(ValueError, match="max_publication_year must be"):
            DataNormalizationConfig(
                min_publication_year=2100, max_publication_year=1800
            )

    def test_negative_min_year(self) -> None:
        """Test validation of negative min year."""
        with pytest.raises(ValueError, match="min_publication_year cannot be negative"):
            DataNormalizationConfig(min_publication_year=-1)

    def test_for_scientific_publications(self) -> None:
        """Test factory method for scientific publications."""
        config = DataNormalizationConfig.for_scientific_publications()
        assert config.min_publication_year == 1800
        assert config.max_publication_year == 2100

    def test_for_modern_publications(self) -> None:
        """Test factory method for modern publications."""
        config = DataNormalizationConfig.for_modern_publications()
        assert config.min_publication_year == 1900


class TestHashPii:
    """Tests for _hash_pii helper method."""

    def test_hash_consistency(self) -> None:
        """Test that same input produces same hash."""
        service = DefaultDataNormalizationService()
        hash1 = service._hash_pii("John Doe", "salt123")
        hash2 = service._hash_pii("John Doe", "salt123")
        assert hash1 == hash2

    def test_different_salt_different_hash(self) -> None:
        """Test that different salt produces different hash."""
        service = DefaultDataNormalizationService()
        hash1 = service._hash_pii("John Doe", "salt1")
        hash2 = service._hash_pii("John Doe", "salt2")
        assert hash1 != hash2

    def test_different_value_different_hash(self) -> None:
        """Test that different value produces different hash."""
        service = DefaultDataNormalizationService()
        hash1 = service._hash_pii("John Doe", "salt")
        hash2 = service._hash_pii("Jane Smith", "salt")
        assert hash1 != hash2
