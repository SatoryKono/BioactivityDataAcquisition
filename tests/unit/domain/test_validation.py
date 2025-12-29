"""Tests for domain.validation module.

Tests pure validation functions per REFACTOR-004.
"""

from __future__ import annotations

import pytest

from bioetl.domain.validation import (
    validate_doi,
    validate_non_empty_string,
    validate_non_negative,
    validate_positive_int,
    validate_smiles,
    validate_year_range,
)


class TestValidateSmiles:
    """Tests for validate_smiles function."""

    @pytest.mark.parametrize(
        "smiles,expected",
        [
            ("CCO", True),  # Ethanol
            ("C1=CC=CC=C1", True),  # Benzene
            ("CC(=O)O", True),  # Acetic acid
            ("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", True),  # Caffeine
            ("c1ccccc1", True),  # Benzene (aromatic)
            ("[Na+].[Cl-]", True),  # NaCl
            ("CC(C)CC", True),  # Isopentane
        ],
    )
    def test_valid_smiles(self, smiles: str, expected: bool) -> None:
        """Test valid SMILES strings are accepted."""
        assert validate_smiles(smiles) is expected

    @pytest.mark.parametrize(
        "smiles",
        [
            "",
            None,
            "   ",
            "invalid smiles with spaces",
            "hello world",
            "123 abc",
        ],
    )
    def test_invalid_smiles(self, smiles: str | None) -> None:
        """Test invalid SMILES strings are rejected."""
        assert validate_smiles(smiles) is False

    def test_smiles_with_whitespace(self) -> None:
        """Test SMILES with leading/trailing whitespace."""
        assert validate_smiles("  CCO  ") is True


class TestValidatePositiveInt:
    """Tests for validate_positive_int function."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (1, 1),
            (42, 42),
            (100, 100),
            ("123", 123),
            (1.9, 1),  # Truncates to int
        ],
    )
    def test_valid_positive_int(self, value, expected: int) -> None:
        """Test valid positive integers are returned."""
        assert validate_positive_int(value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            0,
            -1,
            -100,
            "0",
            "-1",
            None,
            "invalid",
            "",
        ],
    )
    def test_invalid_positive_int(self, value) -> None:
        """Test invalid values return None."""
        assert validate_positive_int(value) is None


class TestValidateYearRange:
    """Tests for validate_year_range function."""

    @pytest.mark.parametrize(
        "year,expected",
        [
            (1800, True),
            (1900, True),
            (2024, True),
            (2100, True),
        ],
    )
    def test_valid_year(self, year: int, expected: bool) -> None:
        """Test valid years in range are accepted."""
        assert validate_year_range(year) is expected

    @pytest.mark.parametrize(
        "year",
        [
            1799,
            2101,
            0,
            -100,
            None,
        ],
    )
    def test_invalid_year(self, year: int | None) -> None:
        """Test invalid years are rejected."""
        assert validate_year_range(year) is False

    def test_custom_range(self) -> None:
        """Test custom year range."""
        assert validate_year_range(1999, min_year=2000, max_year=2050) is False
        assert validate_year_range(2000, min_year=2000, max_year=2050) is True
        assert validate_year_range(2025, min_year=2000, max_year=2050) is True
        assert validate_year_range(2050, min_year=2000, max_year=2050) is True
        assert validate_year_range(2051, min_year=2000, max_year=2050) is False


class TestValidateNonNegative:
    """Tests for validate_non_negative function."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (0, 0.0),
            (0.0, 0.0),
            (42.5, 42.5),
            (100, 100.0),
            ("3.14", 3.14),
        ],
    )
    def test_valid_non_negative(self, value, expected: float) -> None:
        """Test valid non-negative values are returned."""
        assert validate_non_negative(value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            -1,
            -0.001,
            -100.5,
            None,
            "invalid",
            "",
        ],
    )
    def test_invalid_non_negative(self, value) -> None:
        """Test invalid values return None."""
        assert validate_non_negative(value) is None


class TestValidateNonEmptyString:
    """Tests for validate_non_empty_string function."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("hello", "hello"),
            ("  hello  ", "hello"),
            ("test string", "test string"),
        ],
    )
    def test_valid_string(self, value: str, expected: str) -> None:
        """Test valid strings are normalized and returned."""
        assert validate_non_empty_string(value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "   ",
            None,
        ],
    )
    def test_empty_string(self, value: str | None) -> None:
        """Test empty/whitespace strings return None."""
        assert validate_non_empty_string(value) is None


class TestValidateDoi:
    """Tests for validate_doi function."""

    @pytest.mark.parametrize(
        "doi,expected",
        [
            ("10.1038/nature12373", True),
            ("10.1000/xyz123", True),
            ("10.12345/some-thing.here", True),
            ("  10.1038/nature12373  ", True),  # With whitespace
            ("10.1038/NATURE12373", True),  # Uppercase
        ],
    )
    def test_valid_doi(self, doi: str, expected: bool) -> None:
        """Test valid DOIs are accepted."""
        assert validate_doi(doi) is expected

    @pytest.mark.parametrize(
        "doi",
        [
            "",
            None,
            "invalid",
            "11.1038/nature",  # Wrong prefix
            "10.123/nature",  # Registrant too short
            "doi:10.1038/nature",  # With prefix
        ],
    )
    def test_invalid_doi(self, doi: str | None) -> None:
        """Test invalid DOIs are rejected."""
        assert validate_doi(doi) is False
