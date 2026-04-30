"""Tests for DefaultDataNormalizer.

Tests the unified data normalization service for text and publication metadata.
"""

from __future__ import annotations

import json
import unicodedata

import pytest

from bioetl.domain.services import (
    DataNormalizationConfig,
    DefaultDataNormalizer,
)
from bioetl.domain.services._author_helpers import hash_author_name


class TestDefaultDataNormalizerInit:
    """Tests for service initialization."""

    def test_default_config(self) -> None:
        """Test service initializes with default config."""
        service = DefaultDataNormalizer()
        assert service.config.min_publication_year == 1500
        assert service.config.max_publication_year == 2100

    def test_custom_config(self) -> None:
        """Test service accepts custom config."""
        config = DataNormalizationConfig(min_publication_year=1900)
        service = DefaultDataNormalizer(config=config)
        assert service.config.min_publication_year == 1900

    def test_canonical_name_works(self) -> None:
        """Test the canonical DefaultDataNormalizer surface."""
        service = DefaultDataNormalizer()
        assert isinstance(service, DefaultDataNormalizer)


class TestNormalizeDoi:
    """Tests for normalize_doi method."""

    @pytest.mark.parametrize(
        "doi,expected",
        [
            ("10.1038/nature12373", "10.1038/nature12373"),
            ("10.1038/NATURE12373", "10.1038/nature12373"),
            ("  10.1038/nature12373  ", "10.1038/nature12373"),
            ("  10.1038/NATURE12373  ", "10.1038/nature12373"),
            ("https://doi.org/10.1038/NATURE12373", "10.1038/nature12373"),
            ("DOI:10.1001/JAMA.2024.0001", "10.1001/jama.2024.0001"),
            (None, None),
            ("", None),
        ],
    )
    def test_normalize_doi(self, doi: str | None, expected: str | None) -> None:
        """Test DOI normalization."""
        service = DefaultDataNormalizer()
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
            ("9999999999", "9999999999"),
            (None, None),
            ("", None),
            ("abc", None),
            ("12.34", None),
            (0, None),
            (-1, None),
            (10_000_000_000, None),
            ("10000000000", None),
            (True, None),  # Booleans rejected
            (False, None),
        ],
    )
    def test_normalize_pmid(self, pmid: str | int | None, expected: str | None) -> None:
        """Test PMID normalization."""
        service = DefaultDataNormalizer()
        assert service.normalize_pmid(pmid) == expected


class TestNormalizeYear:
    """Tests for normalize_year method."""

    @pytest.mark.parametrize(
        "year,expected_year,expected_warning",
        [
            (2024, 2024, False),
            (1500, 1500, False),
            (2100, 2100, False),
            (1499, 1499, True),
            (2101, 2101, True),
            (1000, 1000, True),
            (None, None, False),
        ],
    )
    def test_normalize_year(
        self, year: int | None, expected_year: int | None, expected_warning: bool
    ) -> None:
        """Test year normalization with default config."""
        service = DefaultDataNormalizer()
        result_year, result_warning = service.normalize_year(year)
        assert result_year == expected_year
        assert result_warning == expected_warning

    def test_normalize_year_custom_range(self) -> None:
        """Test year normalization with custom range."""
        config = DataNormalizationConfig(
            min_publication_year=1900, max_publication_year=2050
        )
        service = DefaultDataNormalizer(config=config)

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
        """Test normalizing list of authors (hashed output)."""
        service = DefaultDataNormalizer()
        result = service.normalize_authors(["John Doe", "Jane Smith"], salt="test")

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2
        # normalize_authors hashes names with salt, so output are hex hashes
        assert all(isinstance(h, str) and len(h) == 64 for h in parsed)

    def test_normalize_authors_string(self) -> None:
        """Test normalizing semicolon-separated authors."""
        service = DefaultDataNormalizer()
        result = service.normalize_authors("John Doe; Jane Smith", salt="test")

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_normalize_authors_json_string(self) -> None:
        """Test normalizing JSON-serialized authors."""
        service = DefaultDataNormalizer()
        result = service.normalize_authors('["John Doe", "Jane Smith"]', salt="test")

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_normalize_authors_empty(self) -> None:
        """Test empty authors returns None."""
        service = DefaultDataNormalizer()
        assert service.normalize_authors(None, salt="test") is None
        assert service.normalize_authors([], salt="test") is None
        assert service.normalize_authors("", salt="test") is None


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
        service = DefaultDataNormalizer()
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
        service = DefaultDataNormalizer()
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
        service = DefaultDataNormalizer()
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
        service = DefaultDataNormalizer()
        assert service.parse_authors_to_list(input_authors) == expected

    def test_parse_authors_semicolon_preference(self) -> None:
        """Test that semicolon takes precedence over comma as delimiter."""
        service = DefaultDataNormalizer()
        # When both semicolon and comma are present, semicolon wins
        result = service.parse_authors_to_list("Doe, John; Smith, Jane")
        assert result == ["Doe, John", "Smith, Jane"]


class TestNormalizePartialDate:
    """Tests for normalize_partial_date method with end of period strategy."""

    @pytest.mark.parametrize(
        "date_str,expected",
        [
            # Full date YYYY-MM-DD - unchanged
            ("2024-03-15", "2024-03-15"),
            ("2024-01-01", "2024-01-01"),
            ("2024-12-31", "2024-12-31"),
            # Partial: YYYY-MM → last day of month
            ("2024-03", "2024-03-31"),
            ("2024-01", "2024-01-31"),
            ("2024-12", "2024-12-31"),
            ("2024-02", "2024-02-29"),
            ("2023-02", "2023-02-28"),
            # Partial: YYYY → YYYY-12-31 (end of year)
            ("2024", "2024-12-31"),
            ("2000", "2000-12-31"),
            ("1999", "1999-12-31"),
            # Whitespace handling
            ("  2024-03-15  ", "2024-03-15"),
            ("  2024-03  ", "2024-03-31"),
            ("  2024  ", "2024-12-31"),
            # None/empty cases
            (None, None),
            ("", None),
            ("   ", None),
            # Invalid formats - return None
            ("2024/03/15", None),
            ("03-15-2024", None),
            ("15-03-2024", None),  # DD-MM-YYYY format is invalid
            ("March 2024", None),  # Text month format is invalid
            ("abc", None),
            ("20241", None),
            ("2024-3", None),  # Invalid: month should be 2 digits
        ],
    )
    def test_normalize_partial_date(
        self, date_str: str | None, expected: str | None
    ) -> None:
        """Test partial date normalization with end of period strategy."""
        service = DefaultDataNormalizer()
        assert service.normalize_partial_date(date_str) == expected


class TestFormatDateParts:
    """Tests for format_date_parts method.

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
            # Year-only: end-of-period (December 31st)
            ([[2024]], "2024-12-31"),
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
        service = DefaultDataNormalizer()
        assert service.format_date_parts(date_parts) == expected


class TestDataNormalizationConfig:
    """Tests for DataNormalizationConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = DataNormalizationConfig()
        assert config.min_publication_year == 1500
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
        assert config.min_publication_year == 1500
        assert config.max_publication_year == 2100

    def test_for_modern_publications(self) -> None:
        """Test factory method for modern publications."""
        config = DataNormalizationConfig.for_modern_publications()
        assert config.min_publication_year == 1900


class TestHashPii:
    """Tests for _hash_pii helper method.

    Per RULES.md §5.4: sha256(lowercase(value) + SALT)
    """

    def test_hash_consistency(self) -> None:
        """Test that same input produces same hash."""
        hash1 = hash_author_name("John Doe", "salt123")
        hash2 = hash_author_name("John Doe", "salt123")
        assert hash1 == hash2

    def test_different_salt_different_hash(self) -> None:
        """Test that different salt produces different hash."""
        hash1 = hash_author_name("John Doe", "salt1")
        hash2 = hash_author_name("John Doe", "salt2")
        assert hash1 != hash2

    def test_different_value_different_hash(self) -> None:
        """Test that different value produces different hash."""
        hash1 = hash_author_name("John Doe", "salt")
        hash2 = hash_author_name("Jane Smith", "salt")
        assert hash1 != hash2

    def test_case_normalization(self) -> None:
        """Test that hashing is case-insensitive per RULES.md §5.4."""
        hash_lower = hash_author_name("john doe", "salt")
        hash_upper = hash_author_name("JOHN DOE", "salt")
        hash_mixed = hash_author_name("John Doe", "salt")
        assert hash_lower == hash_upper == hash_mixed

    def test_whitespace_normalization(self) -> None:
        """Test that leading/trailing whitespace is stripped before hashing."""
        hash_clean = hash_author_name("john doe", "salt")
        hash_padded = hash_author_name("  john doe  ", "salt")
        hash_tabs = hash_author_name("\tjohn doe\t", "salt")
        assert hash_clean == hash_padded == hash_tabs

    def test_hash_formula_matches_rules_md(self) -> None:
        """Test hash formula matches RULES.md §5.4: sha256(lowercase(value) + SALT)."""
        import hashlib

        value = "  John Doe  "
        salt = "test_salt"

        # Expected: sha256(lowercase(stripped(value)) + salt)
        normalized = value.strip().lower()
        expected_hash = hashlib.sha256(f"{normalized}{salt}".encode()).hexdigest()

        actual_hash = hash_author_name(value, salt)
        assert actual_hash == expected_hash

    def test_empty_salt_allowed(self) -> None:
        """Test that empty salt works (edge case)."""
        result = hash_author_name("test", "")
        assert len(result) == 64  # SHA-256 hex digest length


class TestNormalizeTitle:
    """Tests for normalize_title method."""

    @pytest.mark.parametrize(
        "title,expected",
        [
            # Basic normalization
            ("Simple Title", "Simple Title"),
            ("  Title with spaces  ", "Title with spaces"),
            # HTML cleanup
            ("<b>Bold Title</b>", "Bold Title"),
            ("<p>Paragraph <i>italic</i></p>", "Paragraph italic"),
            ("Title with &lt;HTML&gt; entities", "Title with <HTML> entities"),
            ("Title with &amp; &quot;quotes&quot;", 'Title with & "quotes"'),
            # Whitespace normalization
            ("Title  with   multiple    spaces", "Title with multiple spaces"),
            ("Title\twith\ttabs", "Title with tabs"),
            ("Title\nwith\nnewlines", "Title with newlines"),
            ("Title\r\nwith\r\nCRLF", "Title with CRLF"),
            ("  Title  \n  with  \t  mixed  ", "Title with mixed"),
            # Control characters
            ("Title\x00with\x01control", "Titlewithcontrol"),
            ("Title\x7fwith\x9fmore", "Titlewithmore"),
            # Empty/None cases
            (None, None),
            ("", None),
            ("   ", None),
            ("\t\n", None),
            # Unicode normalization (NFC)
            ("Café", "Café"),  # Already NFC
            ("Café", "Café"),  # NFD é (e + combining acute) -> NFC é
            ("naïve", "naïve"),  # NFD ï -> NFC ï
            # Complex cases
            (
                "<b>Title</b>  with   &lt;tags&gt;\nand\twhitespace",
                "Title with <tags> and whitespace",
            ),
            ("  <p>  Study of α-particles  </p>  ", "Study of α-particles"),
        ],
    )
    def test_normalize_title(self, title: str | None, expected: str | None) -> None:
        """Test title normalization with various inputs."""
        service = DefaultDataNormalizer()
        result = service.normalize_title(title)
        assert result == expected

    def test_unicode_nfc_normalization(self) -> None:
        """Test that unicode is normalized to NFC form."""
        service = DefaultDataNormalizer()

        # Create NFD string (decomposed form: e + combining acute accent)
        nfd_title = unicodedata.normalize("NFD", "Café")
        # Verify it's actually NFD
        assert unicodedata.is_normalized("NFD", nfd_title)
        assert not unicodedata.is_normalized("NFC", nfd_title)

        # Normalize should convert to NFC
        result = service.normalize_title(nfd_title)
        assert unicodedata.is_normalized("NFC", result)
        assert result == "Café"

    def test_idempotency(self) -> None:
        """Test that normalization is idempotent."""
        service = DefaultDataNormalizer()
        title = "<b>Test</b>  with   spaces"

        normalized_once = service.normalize_title(title)
        normalized_twice = service.normalize_title(normalized_once)

        assert normalized_once == normalized_twice


class TestNormalizeAbstract:
    """Tests for normalize_abstract method."""

    @pytest.mark.parametrize(
        "abstract,expected",
        [
            # Basic cases
            ("Simple abstract.", "Simple abstract."),
            ("  Abstract with spaces  ", "Abstract with spaces"),
            # HTML cleanup (common in PubMed abstracts)
            ("<p>Background: Study of proteins.</p>", "Background: Study of proteins."),
            (
                "<b>Results:</b> We found <i>p</i> &lt; 0.05",
                "Results: We found p < 0.05",
            ),
            ("Abstract with &alpha;-helix", "Abstract with α-helix"),
            # Whitespace normalization
            ("Line 1\nLine 2\nLine 3", "Line 1 Line 2 Line 3"),
            ("Abstract  with   extra    spaces", "Abstract with extra spaces"),
            # Control characters (can appear in raw data)
            ("Abstract\x00with\x01control", "Abstractwithcontrol"),
            # Empty cases
            (None, None),
            ("", None),
            ("   ", None),
            # Unicode characters (scientific symbols)
            (
                "Study of α-particles and β-radiation",
                "Study of α-particles and β-radiation",
            ),
            ("Temperature ±2°C", "Temperature ±2°C"),
            # Complex real-world case
            (
                "<p><b>Background:</b> Study of &alpha;-helix.\n\n"
                "<b>Methods:</b>  We analyzed  proteins.</p>",
                "Background: Study of α-helix. Methods: We analyzed proteins.",
            ),
        ],
    )
    def test_normalize_abstract(
        self, abstract: str | None, expected: str | None
    ) -> None:
        """Test abstract normalization with various inputs."""
        service = DefaultDataNormalizer()
        result = service.normalize_abstract(abstract)
        assert result == expected

    def test_preserves_special_characters(self) -> None:
        """Test that scientific special characters are preserved."""
        service = DefaultDataNormalizer()

        abstract = "Study found p<0.05, R²=0.98, ±2σ, α=0.01"
        result = service.normalize_abstract(abstract)

        # Special characters should be preserved
        assert "p<0.05" in result
        assert "R²=0.98" in result
        assert "±2σ" in result
        assert "α=0.01" in result

    def test_long_abstract_performance(self) -> None:
        """Test normalization of long abstracts (performance check)."""
        service = DefaultDataNormalizer()

        # Create a long abstract (typical length ~3000 chars)
        long_abstract = "<p>" + ("Study of proteins. " * 150) + "</p>"

        # Should complete without issues
        result = service.normalize_abstract(long_abstract)
        assert result is not None
        assert len(result) > 2000
