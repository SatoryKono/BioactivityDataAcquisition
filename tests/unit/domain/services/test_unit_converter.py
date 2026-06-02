"""Unit tests for UnitConverter service."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.unit_converter import UnitConverter
from bioetl.domain.value_objects import (
    Concentration,
    ConcentrationUnit,
    PChemblValue,
)


pytestmark = pytest.mark.unit


class TestUnitConverter:
    """Tests for UnitConverter service."""

    @pytest.fixture
    def converter(self) -> UnitConverter:
        """Create a UnitConverter instance."""
        return UnitConverter()

    # ==========================================================================
    # convert() tests
    # ==========================================================================

    def test_convert_nm_to_um(self, converter: UnitConverter) -> None:
        """Test conversion from nanomolar to micromolar."""
        result = converter.convert(1000.0, "nM", "uM")
        assert result == pytest.approx(1.0)

    def test_convert_um_to_nm(self, converter: UnitConverter) -> None:
        """Test conversion from micromolar to nanomolar."""
        result = converter.convert(1.0, "uM", "nM")
        assert result == pytest.approx(1000.0)

    def test_convert_um_alias(self, converter: UnitConverter) -> None:
        """Test that uM is an alias for uM."""
        result = converter.convert(100.0, "uM", "nM")
        assert result == pytest.approx(100000.0)

    def test_convert_same_unit(self, converter: UnitConverter) -> None:
        """Test conversion to same unit returns original value."""
        result = converter.convert(42.5, "nM", "nM")
        assert result == pytest.approx(42.5)

    def test_convert_mm_to_nm(self, converter: UnitConverter) -> None:
        """Test conversion from millimolar to nanomolar."""
        result = converter.convert(1.0, "mM", "nM")
        assert result == pytest.approx(1_000_000.0)

    def test_convert_pm_to_nm(self, converter: UnitConverter) -> None:
        """Test conversion from picomolar to nanomolar."""
        result = converter.convert(1000.0, "pM", "nM")
        assert result == pytest.approx(1.0)

    def test_convert_invalid_unit_raises(self, converter: UnitConverter) -> None:
        """Test that invalid units raise ValueError."""
        with pytest.raises(ValueError, match="Unknown concentration unit"):
            converter.convert(100.0, "invalid", "nM")

    def test_convert_negative_value_raises(self, converter: UnitConverter) -> None:
        """Test that negative values raise ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            converter.convert(-100.0, "nM", "uM")

    # ==========================================================================
    # to_concentration() tests
    # ==========================================================================

    def test_to_concentration_creates_value_object(
        self, converter: UnitConverter
    ) -> None:
        """Test creation of Concentration value object."""
        result = converter.to_concentration(100.0, "nM")
        assert isinstance(result, Concentration)
        assert result.value == pytest.approx(100.0)
        assert result.unit == ConcentrationUnit.NANOMOLAR

    def test_to_concentration_micromolar(self, converter: UnitConverter) -> None:
        """Test creation with micromolar unit."""
        result = converter.to_concentration(1.5, "uM")
        assert result.value == pytest.approx(1.5)
        assert result.unit == ConcentrationUnit.MICROMOLAR

    def test_to_concentration_negative_raises(self, converter: UnitConverter) -> None:
        """Test that negative values raise ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            converter.to_concentration(-50.0, "nM")

    # ==========================================================================
    # to_pchembl() tests
    # ==========================================================================

    def test_to_pchembl_100nm(self, converter: UnitConverter) -> None:
        """Test pChEMBL calculation for 100 nM."""
        conc = Concentration(100.0, ConcentrationUnit.NANOMOLAR)
        result = converter.to_pchembl(conc)
        assert isinstance(result, PChemblValue)
        # 100 nM = 1e-7 M, -log10(1e-7) = 7
        assert result.value == pytest.approx(7.0)

    def test_to_pchembl_1um(self, converter: UnitConverter) -> None:
        """Test pChEMBL calculation for 1 uM."""
        conc = Concentration(1.0, ConcentrationUnit.MICROMOLAR)
        result = converter.to_pchembl(conc)
        # 1 uM = 1e-6 M, -log10(1e-6) = 6
        assert result.value == pytest.approx(6.0)

    def test_to_pchembl_10nm(self, converter: UnitConverter) -> None:
        """Test pChEMBL calculation for 10 nM (highly potent)."""
        conc = Concentration(10.0, ConcentrationUnit.NANOMOLAR)
        result = converter.to_pchembl(conc)
        # 10 nM = 1e-8 M, -log10(1e-8) = 8
        assert result.value == pytest.approx(8.0)

    # ==========================================================================
    # pchembl_to_concentration() tests
    # ==========================================================================

    def test_pchembl_to_concentration_7(self, converter: UnitConverter) -> None:
        """Test conversion of pChEMBL 7 to concentration."""
        pchembl = PChemblValue(7.0)
        result = converter.pchembl_to_concentration(pchembl)
        # pChEMBL 7 = 100 nM
        assert result.value == pytest.approx(100.0, rel=1e-6)
        assert result.unit == ConcentrationUnit.NANOMOLAR

    def test_pchembl_to_concentration_with_string_unit(
        self, converter: UnitConverter
    ) -> None:
        """Test conversion with string unit specification."""
        pchembl = PChemblValue(6.0)
        result = converter.pchembl_to_concentration(pchembl, "uM")
        # pChEMBL 6 = 1 uM
        assert result.value == pytest.approx(1.0, rel=1e-6)
        assert result.unit == ConcentrationUnit.MICROMOLAR

    # ==========================================================================
    # normalize_to_nanomolar() tests
    # ==========================================================================

    def test_normalize_to_nanomolar(self, converter: UnitConverter) -> None:
        """Test normalization to nanomolar."""
        result = converter.normalize_to_nanomolar(1.0, "uM")
        assert result == pytest.approx(1000.0)

    def test_normalize_to_nanomolar_from_nm(self, converter: UnitConverter) -> None:
        """Test normalization from nanomolar (no-op)."""
        result = converter.normalize_to_nanomolar(100.0, "nM")
        assert result == pytest.approx(100.0)

    # ==========================================================================
    # normalize_to_micromolar() tests
    # ==========================================================================

    def test_normalize_to_micromolar(self, converter: UnitConverter) -> None:
        """Test normalization to micromolar."""
        result = converter.normalize_to_micromolar(1000.0, "nM")
        assert result == pytest.approx(1.0)

    # ==========================================================================
    # value_to_pchembl() tests
    # ==========================================================================

    def test_value_to_pchembl(self, converter: UnitConverter) -> None:
        """Test direct conversion from value+unit to pChEMBL."""
        result = converter.value_to_pchembl(100.0, "nM")
        assert result.value == pytest.approx(7.0)

    def test_value_to_pchembl_micromolar(self, converter: UnitConverter) -> None:
        """Test pChEMBL from micromolar value."""
        result = converter.value_to_pchembl(10.0, "uM")
        # 10 uM = 1e-5 M, -log10(1e-5) = 5
        assert result.value == pytest.approx(5.0)


class TestUnitConverterEdgeCases:
    """Edge case tests for UnitConverter."""

    @pytest.fixture
    def converter(self) -> UnitConverter:
        return UnitConverter()

    def test_very_small_concentration(self, converter: UnitConverter) -> None:
        """Test conversion of very small (femtomolar) concentration."""
        result = converter.convert(1.0, "fM", "nM")
        assert result == pytest.approx(1e-6)

    def test_very_large_concentration(self, converter: UnitConverter) -> None:
        """Test conversion of large (millimolar) concentration."""
        result = converter.convert(100.0, "mM", "nM")
        assert result == pytest.approx(1e8)

    def test_high_precision_preserved(self, converter: UnitConverter) -> None:
        """Test that precision is preserved in conversions."""
        result = converter.convert(1.23456789, "nM", "pM")
        # nM to pM = multiply by 1000
        assert result == pytest.approx(1234.56789, rel=1e-9)
