"""Tests for chemical structure validation functions.

Tests for validate_smiles, validate_molecular_weight, validate_inchi_key.
"""

from __future__ import annotations

import pytest

from bioetl.domain.config.validation import ValidationConfig
from bioetl.domain.validation.chemical import (
    INCHI_KEY_REGEX_PATTERN,
    MAX_MOLECULAR_WEIGHT,
    MIN_MOLECULAR_WEIGHT,
    validate_inchi_key,
    validate_molecular_weight,
    validate_smiles,
)


@pytest.mark.unit
class TestValidateSmiles:
    """Tests for validate_smiles function."""

    def test_valid_ethanol(self) -> None:
        assert validate_smiles("CCO") is True

    def test_valid_benzene(self) -> None:
        assert validate_smiles("C1=CC=CC=C1") is True

    def test_valid_aspirin(self) -> None:
        assert validate_smiles("CC(=O)Oc1ccccc1C(=O)O") is True

    def test_valid_with_brackets(self) -> None:
        assert validate_smiles("[Na+].[Cl-]") is True

    def test_valid_with_stereochemistry(self) -> None:
        assert validate_smiles("C(/F)=C/F") is True

    def test_empty_string_returns_false(self) -> None:
        assert validate_smiles("") is False

    def test_none_returns_false(self) -> None:
        assert validate_smiles(None) is False

    def test_whitespace_only_returns_false(self) -> None:
        assert validate_smiles("   ") is False

    def test_spaces_in_string_returns_false(self) -> None:
        assert validate_smiles("invalid smiles with spaces") is False

    def test_strips_whitespace(self) -> None:
        assert validate_smiles("  CCO  ") is True


@pytest.mark.unit
class TestValidateMolecularWeight:
    """Tests for validate_molecular_weight function."""

    def test_valid_float(self) -> None:
        result = validate_molecular_weight(180.16)
        assert result is not None
        assert abs(result - 180.16) < 1e-6

    def test_valid_int(self) -> None:
        result = validate_molecular_weight(500)
        assert result is not None
        assert result == pytest.approx(500.0)

    def test_valid_string(self) -> None:
        result = validate_molecular_weight("250.5")
        assert result is not None
        assert abs(result - 250.5) < 1e-6

    def test_none_returns_none(self) -> None:
        assert validate_molecular_weight(None) is None

    def test_bool_returns_none(self) -> None:
        assert validate_molecular_weight(True) is None
        assert validate_molecular_weight(False) is None

    def test_invalid_string_returns_none(self) -> None:
        assert validate_molecular_weight("not_a_number") is None

    def test_zero_returns_none_with_default_bounds(self) -> None:
        # MIN_MOLECULAR_WEIGHT is 0.0 (exclusive), so 0.0 should return None
        assert validate_molecular_weight(0.0) is None

    def test_negative_returns_none(self) -> None:
        assert validate_molecular_weight(-100.0) is None

    def test_exceeds_max_returns_none(self) -> None:
        assert validate_molecular_weight(MAX_MOLECULAR_WEIGHT + 1) is None

    def test_custom_config_bounds(self) -> None:
        config = ValidationConfig(
            min_molecular_weight=100.0, max_molecular_weight=500.0
        )
        assert validate_molecular_weight(250.0, config=config) is not None
        assert validate_molecular_weight(50.0, config=config) is None
        assert validate_molecular_weight(600.0, config=config) is None

    def test_whitespace_string(self) -> None:
        result = validate_molecular_weight("  180.16  ")
        assert result is not None


@pytest.mark.unit
class TestValidateInchiKey:
    """Tests for validate_inchi_key function."""

    def test_valid_aspirin(self) -> None:
        assert validate_inchi_key("BSYNRYMUTXBXSQ-UHFFFAOYSA-N") is True

    def test_valid_caffeine(self) -> None:
        assert validate_inchi_key("RYYVLZVUVIJVGH-UHFFFAOYSA-N") is True

    def test_lowercase_returns_false(self) -> None:
        assert validate_inchi_key("bsynrymutxbxsq-uhfffaoysa-n") is False

    def test_invalid_format_returns_false(self) -> None:
        assert validate_inchi_key("invalid") is False

    def test_none_returns_false(self) -> None:
        assert validate_inchi_key(None) is False

    def test_empty_string_returns_false(self) -> None:
        assert validate_inchi_key("") is False

    def test_too_short_returns_false(self) -> None:
        assert validate_inchi_key("ABCDEFGHIJKLMN-OPQRSTUVWX") is False

    def test_strips_whitespace(self) -> None:
        assert validate_inchi_key("  BSYNRYMUTXBXSQ-UHFFFAOYSA-N  ") is True

    def test_regex_pattern_is_exported(self) -> None:
        assert INCHI_KEY_REGEX_PATTERN == r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$"

    def test_constants_exported(self) -> None:
        assert MIN_MOLECULAR_WEIGHT == pytest.approx(0.0)
        assert MAX_MOLECULAR_WEIGHT == pytest.approx(100000.0)
