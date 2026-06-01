"""Tests for domain.validation module.

Tests pure validation functions per REFACTOR-004.
"""

from __future__ import annotations

import pytest

from bioetl.domain.validation import (
    MAX_MOLECULAR_WEIGHT,
    MAX_PUBLICATION_YEAR,
    MIN_MOLECULAR_WEIGHT,
    MIN_PUBLICATION_YEAR,
    validate_doi,
    validate_inchi_key,
    validate_molecular_weight,
    validate_non_empty_string,
    validate_non_negative,
    validate_positive_int,
    validate_publication_year,
    validate_smiles,
    validate_year_range,
)


pytestmark = pytest.mark.unit

class TestValidateSmiles:
    """Tests for validate_smiles function."""

    @pytest.mark.parametrize(
        "smiles,expected",
        [
            ("CCO", True),  # Ethanol
            ("C1=CC=CC=C1", True),  # Benzene
            ("CC(=O)O", True),  # Acetic amolecule_id
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
            (1500, False),
            (1990, True),
            (2024, True),
            (2100, False),
        ],
    )
    def test_valid_year(self, year: int, expected: bool) -> None:
        """Test valid years in range are accepted."""
        assert validate_year_range(year) is expected

    def test_valid_year_current(self) -> None:
        """Test that current year is valid."""
        assert validate_year_range(2024) is True

    @pytest.mark.parametrize(
        "year",
        [
            1499,
            0,
            -100,
            2101,
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


class TestPublicationYearConstants:
    """Tests for publication year constants."""

    def test_min_publication_year_value(self) -> None:
        """Test MIN_PUBLICATION_YEAR is set to 1950."""
        assert MIN_PUBLICATION_YEAR == 1950

    def test_max_publication_year_value(self) -> None:
        """Test MAX_PUBLICATION_YEAR is 2100."""
        assert MAX_PUBLICATION_YEAR == 2050

    def test_constants_are_valid_range(self) -> None:
        """Test that min < max for valid range."""
        assert MIN_PUBLICATION_YEAR < MAX_PUBLICATION_YEAR


class TestValidatePublicationYear:
    """Tests for validate_publication_year function.

    The function returns (year, is_warning) tuple where:
    - year: Original value (preserved even if out of range)
    - is_warning: True if year is outside valid range (requires DQ warning)
    """

    @pytest.mark.parametrize(
        "year,expected_warn",
        [
            (2020, False),
            (1500, False),
            (2100, False),
            (1499, True),
            (2101, True),
            (1000, True),
            (None, False),
        ],
    )
    def test_publication_year__publication_year__4c15c71d(
        self, year: int | None, expected_warn: bool
    ) -> None:
        """Test validate_publication_year returns correct warning flag."""
        result_year, is_warn = validate_publication_year(year)
        assert result_year == year
        assert is_warn == expected_warn

    def test_validate_publication_year_boundaries(self) -> None:
        """Test that 2100 is valid, 2101 warns."""
        assert validate_publication_year(2100) == (2100, False)
        assert validate_publication_year(2101) == (2101, True)

    def test_boundary_values(self) -> None:
        """Test boundary values for publication year validation."""
        # At boundaries (valid)
        assert validate_publication_year(1500) == (1500, False)
        assert validate_publication_year(2100) == (2100, False)

        # Just outside boundaries (warning)
        assert validate_publication_year(1499) == (1499, True)
        assert validate_publication_year(2101) == (2101, True)

    def test_preserves_original_value(self) -> None:
        """Test that original value is preserved even when out of range."""
        # Test with clearly invalid years
        year, is_warn = validate_publication_year(1000)
        assert year == 1000
        assert is_warn is True

        year, is_warn = validate_publication_year(3000)
        assert year == 3000
        assert is_warn is True

    def test_none_returns_no_warning(self) -> None:
        """Test that None value returns no warning."""
        year, is_warn = validate_publication_year(None)
        assert year is None
        assert is_warn is False


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


class TestMolecularWeightConstants:
    """Tests for molecular weight constants."""

    def test_min_molecular_weight_value(self) -> None:
        """Test MIN_MOLECULAR_WEIGHT is set to 0.0."""
        assert MIN_MOLECULAR_WEIGHT == pytest.approx(0.0)

    def test_max_molecular_weight_value(self) -> None:
        """Test MAX_MOLECULAR_WEIGHT is set to 100000.0."""
        assert MAX_MOLECULAR_WEIGHT == pytest.approx(100000.0)

    def test_constants_are_valid_range__test_molecular_weight_constants_unit_domain_test_validation_265(
        self,
    ) -> None:
        """Test that min < max for valid range."""
        assert MIN_MOLECULAR_WEIGHT < MAX_MOLECULAR_WEIGHT


class TestValidateMolecularWeight:
    """Tests for validate_molecular_weight function.

    Validates molecular weight with:
    - String to float conversion (PubChem API returns strings)
    - Range validation: 0 < mw < 100000
    - Precision: 10 decimals per RULES.md §2.8.1
    """

    @pytest.mark.parametrize(
        "value,expected",
        [
            # Standard float values
            (180.156, 180.156),
            (342.3, 342.3),
            (12.0, 12.0),
            (99999.9, 99999.9),
            # Integer values
            (100, 100.0),
            (500, 500.0),
            # String values (PubChem API format)
            ("180.156", 180.156),
            ("342.30", 342.3),
            ("100", 100.0),
            # Edge cases near boundaries
            (0.001, 0.001),  # Just above 0
            (99999.999, 99999.999),  # Just below max
        ],
    )
    def test_valid_molecular_weight(self, value, expected: float) -> None:
        """Test valid molecular weights are converted and returned."""
        assert validate_molecular_weight(value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            # Zero and negative
            0,
            0.0,
            -1,
            -0.001,
            -100.5,
            # Too large (>= 100000)
            100000,
            100000.0,
            100001,
            150000.5,
            # Invalid types
            None,
            "invalid",
            "",
            "abc",
            # Edge cases
            float("inf"),
            float("-inf"),
        ],
    )
    def test_invalid_molecular_weight(self, value) -> None:
        """Test invalid values return None."""
        assert validate_molecular_weight(value) is None

    def test_nan_returns_none(self) -> None:
        """Test NaN returns None (comparison with NaN is always False)."""
        result = validate_molecular_weight(float("nan"))
        assert result is None

    def test_precision_10_decimals(self) -> None:
        """Test molecular weight is rounded to 10 decimals per RULES.md §2.8.1."""
        # Value with many decimals should be rounded
        result = validate_molecular_weight(180.12345678901234567890)
        assert result is not None
        # Check precision is 10 decimals
        assert result == round(180.12345678901234567890, 10)

    def test_string_conversion_from_api(self) -> None:
        """Test string values from PubChem API are properly converted."""
        # PubChem may return molecular weight as string
        assert validate_molecular_weight("180.156") == pytest.approx(180.156)
        assert validate_molecular_weight("  342.30  ") == pytest.approx(
            342.3
        )  # Whitespace handled

    def test_boundary_values__test_validate_molecular_weight_unit_domain_test_validation_352(
        self,
    ) -> None:
        """Test boundary values for molecular weight validation."""
        # Just above 0 (valid)
        assert validate_molecular_weight(0.0000000001) is not None

        # At 0 (invalid - must be > 0)
        assert validate_molecular_weight(0) is None

        # Just below max (valid)
        assert validate_molecular_weight(99999.9999999999) is not None

        # At max (invalid - must be < 100000)
        assert validate_molecular_weight(100000) is None


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
    def test_non_empty_string__valid_string__56593c57(self, value: str, expected: str) -> None:
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
    def test_non_empty_string__empty_string__634b4163(self, value: str | None) -> None:
        """Test empty/whitespace strings return None."""
        assert validate_non_empty_string(value) is None


class TestValidateDoi:
    """Tests for validate_doi function."""

    @pytest.mark.parametrize(
        "doi,expected",
        [
            # Valid DOIs - standard format
            ("10.1038/nature12373", True),
            ("10.1000/xyz123", True),
            ("10.12345/some-thing.here", True),
            ("  10.1038/nature12373  ", True),  # With whitespace
            ("10.1038/NATURE12373", True),  # Uppercase
            # Valid DOIs - minimum registrant (4 digits)
            ("10.1234/a", True),
            ("10.9999/suffix", True),
            # Valid DOIs - longer registrant codes
            ("10.1234567890/a", True),
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
            "10.123/nature",  # Registrant too short (3 digits)
            "10.12/nature",  # Registrant too short (2 digits)
            "10.1/nature",  # Registrant too short (1 digit)
            "doi:10.1038/nature",  # With prefix
            "10.1234/",  # Empty suffix
            "10.1234",  # No suffix at all
        ],
    )
    def test_invalid_doi(self, doi: str | None) -> None:
        """Test invalid DOIs are rejected."""
        assert validate_doi(doi) is False

    @pytest.mark.parametrize(
        "registrant_digits",
        [1, 2, 3],
    )
    def test_short_registrant_rejected(self, registrant_digits: int) -> None:
        """Test registrant codes with < 4 digits are rejected."""
        registrant = "1" * registrant_digits
        doi = f"10.{registrant}/suffix"
        assert validate_doi(doi) is False

    @pytest.mark.parametrize(
        "registrant_digits",
        [4, 5, 6, 10],
    )
    def test_valid_registrant_lengths(self, registrant_digits: int) -> None:
        """Test registrant codes with >= 4 digits are accepted."""
        registrant = "1" * registrant_digits
        doi = f"10.{registrant}/suffix"
        assert validate_doi(doi) is True


class TestValidateInchiKey:
    """Tests for validate_inchi_key function."""

    @pytest.mark.parametrize(
        "inchi_key,expected",
        [
            # Valid InChI Keys - real examples
            ("BSYNRYMUTXBXSQ-UHFFFAOYSA-N", True),  # Aspirin
            ("RYYVLZVUVIJVGH-UHFFFAOYSA-N", True),  # Caffeine
            ("HEFNNWSXXWATRW-UHFFFAOYSA-N", True),  # Paracetamol
            ("RZVAJINKPMORJF-UHFFFAOYSA-N", True),  # Ibuprofen
            # Valid InChI Keys - format check
            ("XXXXXXXXXXXXXX-YYYYYYYYYY-Z", True),
            ("ABCDEFGHIJKLMN-OPQRSTUVWX-Y", True),
        ],
    )
    def test_valid_inchi_key(self, inchi_key: str, expected: bool) -> None:
        """Test valid InChI Keys are accepted."""
        assert validate_inchi_key(inchi_key) is expected

    @pytest.mark.parametrize(
        "inchi_key",
        [
            "",
            None,
            "   ",
            "invalid",
            "bsynrymutxbxsq-uhfffaoysa-n",  # Lowercase
            "BSYNRYMUTXBXSQ-UHFFFAOYSA",  # Missing last part
            "BSYNRYMUTXBXSQ-UHFFFAOYSAA-N",  # Too long middle (11 chars)
            "BSYNRYMUTXBXS-UHFFFAOYSA-N",  # Too short first (13 chars)
            "BSYNRYMUTXBXSQA-UHFFFAOYSA-N",  # Too long first (15 chars)
            "BSYNRYMUTXBXSQ-UHFFFAOYS-N",  # Too short middle (9 chars)
            "BSYNRYMUTXBXSQ-UHFFFAOYSA-",  # Empty last part
            "BSYNRYMUTXBXSQ-UHFFFAOYSA-NN",  # Too long last part (2 chars)
            "BSYNRYMUTXBXSQ_UHFFFAOYSA_N",  # Wrong separator
            "BSYNRYMUTXBXSQUHFFFAOYSAN",  # No separators
            "123456789012345-1234567890-X",  # Numbers instead of letters
        ],
    )
    def test_invalid_inchi_key(self, inchi_key: str | None) -> None:
        """Test invalid InChI Keys are rejected."""
        assert validate_inchi_key(inchi_key) is False

    def test_inchi_key_with_whitespace(self) -> None:
        """Test InChI Key with leading/trailing whitespace."""
        assert validate_inchi_key("  BSYNRYMUTXBXSQ-UHFFFAOYSA-N  ") is True

    def test_inchi_key_case_sensitive(self) -> None:
        """Test InChI Key validation is case-sensitive (uppercase only)."""
        # Uppercase should pass
        assert validate_inchi_key("BSYNRYMUTXBXSQ-UHFFFAOYSA-N") is True
        # Lowercase should fail
        assert validate_inchi_key("bsynrymutxbxsq-uhfffaoysa-n") is False
        # Mixed case should fail
        assert validate_inchi_key("BSYNRYMUTXBXSQ-uhfffaoysa-N") is False
