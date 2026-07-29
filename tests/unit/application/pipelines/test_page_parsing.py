# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for page parsing and PMC ID normalization domain functions.

Tests the parse_page_range and normalize_pmc_id functions from domain/normalization.py
that are used by PubMed and SemanticScholar transformers for parsing page strings
and normalizing PMC IDs.

Note: These tests complement the tests in tests/unit/domain/test_normalization.py
by testing additional edge cases relevant to publication transformers.
"""

from __future__ import annotations

import pytest

from bioetl.domain.normalization import normalize_pmc_id, parse_page_range


@pytest.mark.unit
class TestPubMedMedlinePgnParsing:
    """Tests for PubMed medline_pgn parsing using domain function."""

    @pytest.mark.parametrize(
        "pgn,expected_first,expected_last",
        [
            # Standard hyphenated range
            ("100-110", "100", "110"),
            ("1-999", "1", "999"),
            ("123-456", "123", "456"),
            # Single page number
            ("100", "100", None),
            ("1", "1", None),
            ("999999", "999999", None),
            # Electronic article numbers
            ("e100-e110", "e100", "e110"),
            ("E123-E456", "E123", "E456"),
            # Supplement pages
            ("S1-S10", "S1", "S10"),
            ("s100-s200", "s100", "s200"),
            # Short form (abbreviated last page - expanded)
            ("100-10", "100", "110"),
            ("1234-56", "1234", "1256"),
            # Empty and None
            ("", None, None),
            (None, None, None),
            # Whitespace handling
            ("  100 - 110  ", "100", "110"),
            ("100 -110", "100", "110"),
            ("  100  ", "100", None),
            # Mixed formats
            ("A1-A10", "A1", "A10"),
            ("ii-x", "ii", "x"),
        ],
    )
    def test_parse_medline_pgn(
        self,
        pgn: str | None,
        expected_first: str | None,
        expected_last: str | None,
    ) -> None:
        """Test various medline_pgn formats."""
        first, last = parse_page_range(pgn)

        assert first == expected_first, f"First page mismatch for '{pgn}'"
        assert last == expected_last, f"Last page mismatch for '{pgn}'"

    def test_hyphen_only_returns_empty(self) -> None:
        """Single hyphen should return None for both values."""
        first, last = parse_page_range("-")

        assert first is None
        assert last is None

    def test_parse_pages_immutability(self) -> None:
        """Parsing should not modify the original string."""
        original = "100-110"
        _ = parse_page_range(original)

        assert original == "100-110"


@pytest.mark.unit
class TestSemanticScholarPagesParsing:
    """Tests for Semantic Scholar pages parsing using domain function."""

    @pytest.mark.parametrize(
        "pages,expected_first,expected_last",
        [
            # Standard hyphenated range
            ("123-456", "123", "456"),
            ("1-10", "1", "10"),
            # Single page
            ("123", "123", None),
            ("1", "1", None),
            # Electronic articles
            ("e123-e456", "e123", "e456"),
            # Empty and None
            (None, None, None),
            ("", None, None),
            # Whitespace
            ("  100 - 200  ", "100", "200"),
            # Single page with whitespace
            ("  100  ", "100", None),
        ],
    )
    def test_parse_pages(
        self,
        pages: str | None,
        expected_first: str | None,
        expected_last: str | None,
    ) -> None:
        """Test various pages formats from Semantic Scholar."""
        first, last = parse_page_range(pages)

        assert first == expected_first, f"First page mismatch for '{pages}'"
        assert last == expected_last, f"Last page mismatch for '{pages}'"


@pytest.mark.unit
class TestPageParsingConsistency:
    """Tests for consistency of page parsing across common formats.

    Since both PubMed and SemanticScholar transformers now use the same
    domain function (parse_page_range), this test verifies the function
    handles all common formats consistently.
    """

    @pytest.mark.parametrize(
        "pages",
        [
            "100-200",
            "123",
            "e100-e200",
            None,
            "",
            "  100 - 200  ",
        ],
    )
    def test_parsing_consistency(self, pages: str | None) -> None:
        """Domain function should parse common formats consistently."""
        first, last = parse_page_range(pages)

        # Verify return type consistency
        if pages and pages.strip():
            # For non-empty input, first should always be populated
            assert first is not None or pages.strip() == "-"
        else:
            # For empty/None input, both should be None
            assert first is None
            assert last is None


@pytest.mark.unit
class TestPmcIdNormalization:
    """Tests for PMC ID normalization using domain function."""

    @pytest.mark.parametrize(
        "raw_pmc_id,expected",
        [
            # Already normalized
            ("PMC1234567", "PMC1234567"),
            # Lowercase PMC prefix
            ("pmc1234567", "PMC1234567"),
            # Missing prefix - should add PMC
            ("1234567", "PMC1234567"),
            # Mixed case
            ("Pmc1234567", "PMC1234567"),
            # None and empty
            (None, None),
            ("", None),
            # Whitespace
            ("  PMC1234567  ", "PMC1234567"),
            ("  1234567  ", "PMC1234567"),
        ],
    )
    def test_pmc_id_normalization(
        self,
        raw_pmc_id: str | None,
        expected: str | None,
    ) -> None:
        """Domain function should normalize PMC IDs correctly."""
        result = normalize_pmc_id(raw_pmc_id)
        assert result == expected


@pytest.mark.unit
class TestPmcIdNormalizationEdgeCases:
    """Additional edge case tests for PMC ID normalization."""

    def test_only_whitespace_returns_none(self) -> None:
        """Only whitespace should return None."""
        assert normalize_pmc_id("   ") is None

    def test_pmc_prefix_variations(self) -> None:
        """Test various PMC prefix capitalizations."""
        assert normalize_pmc_id("PMC123") == "PMC123"
        assert normalize_pmc_id("pmc123") == "PMC123"
        assert normalize_pmc_id("Pmc123") == "PMC123"
        assert normalize_pmc_id("pMc123") == "PMC123"

    def test_numeric_only_input(self) -> None:
        """Numeric-only input should get PMC prefix added."""
        assert normalize_pmc_id("123") == "PMC123"
        assert normalize_pmc_id("1234567890") == "PMC1234567890"
