# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for measurement Value Objects.

Tests for Concentration, ConcentrationUnit, ActivityType, PChemblValue.
"""

from __future__ import annotations

import math

import pytest

from bioetl.domain.value_objects import (
    ActivityType,
    Concentration,
    ConcentrationUnit,
    PChemblValue,
)

pytestmark = pytest.mark.unit


class TestConcentrationUnit:
    """Tests for ConcentrationUnit enum."""

    def test_molar_factor(self) -> None:
        """Test molar conversion factors."""
        assert math.isclose(ConcentrationUnit.MOLAR.to_molar_factor, 1.0)
        assert math.isclose(ConcentrationUnit.MILLIMOLAR.to_molar_factor, 1e-3)
        assert math.isclose(ConcentrationUnit.MICROMOLAR.to_molar_factor, 1e-6)
        assert math.isclose(ConcentrationUnit.NANOMOLAR.to_molar_factor, 1e-9)
        assert math.isclose(ConcentrationUnit.PICOMOLAR.to_molar_factor, 1e-12)
        assert math.isclose(ConcentrationUnit.FEMTOMOLAR.to_molar_factor, 1e-15)

    def test_from_string_nm(self) -> None:
        """Test parsing nanomolar unit."""
        assert ConcentrationUnit.from_string("nM") == ConcentrationUnit.NANOMOLAR
        assert ConcentrationUnit.from_string("nm") == ConcentrationUnit.NANOMOLAR
        assert ConcentrationUnit.from_string("NM") == ConcentrationUnit.NANOMOLAR

    def test_from_string_um(self) -> None:
        """Test parsing micromolar unit with various spellings."""
        assert ConcentrationUnit.from_string("μM") == ConcentrationUnit.MICROMOLAR
        assert ConcentrationUnit.from_string("uM") == ConcentrationUnit.MICROMOLAR
        assert ConcentrationUnit.from_string("um") == ConcentrationUnit.MICROMOLAR
        assert ConcentrationUnit.from_string("microM") == ConcentrationUnit.MICROMOLAR

    def test_from_string_mm(self) -> None:
        """Test parsing millimolar unit."""
        assert ConcentrationUnit.from_string("mM") == ConcentrationUnit.MILLIMOLAR
        assert ConcentrationUnit.from_string("mm") == ConcentrationUnit.MILLIMOLAR

    def test_from_string_pm(self) -> None:
        """Test parsing picomolar unit."""
        assert ConcentrationUnit.from_string("pM") == ConcentrationUnit.PICOMOLAR
        assert ConcentrationUnit.from_string("pm") == ConcentrationUnit.PICOMOLAR

    def test_from_string_fm(self) -> None:
        """Test parsing femtomolar unit."""
        assert ConcentrationUnit.from_string("fM") == ConcentrationUnit.FEMTOMOLAR

    def test_from_string_m(self) -> None:
        """Test parsing molar unit."""
        assert ConcentrationUnit.from_string("M") == ConcentrationUnit.MOLAR
        assert ConcentrationUnit.from_string("m") == ConcentrationUnit.MOLAR

    def test_concentration__invalid_raises__72b0ed87(self) -> None:
        """Test invalid unit string raises ValueError."""
        with pytest.raises(ValueError, match="Unknown concentration unit"):
            ConcentrationUnit.from_string("kg")

    def test_concentration__strips_whitespace__d4687158(self) -> None:
        """Test whitespace is stripped."""
        assert ConcentrationUnit.from_string("  nM  ") == ConcentrationUnit.NANOMOLAR


class TestConcentration:
    """Tests for Concentration Value Object."""

    def test_concentration__creation__8baced23(self) -> None:
        """Test basic creation."""
        c = Concentration(value=100.0, unit=ConcentrationUnit.NANOMOLAR)
        assert c.value == pytest.approx(100.0)
        assert c.unit == ConcentrationUnit.NANOMOLAR

    def test_zero_concentration(self) -> None:
        """Test zero concentration is valid."""
        c = Concentration(value=0.0, unit=ConcentrationUnit.NANOMOLAR)
        assert c.value == pytest.approx(0.0)

    def test_negative_concentration_raises(self) -> None:
        """Test negative concentration raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            Concentration(value=-1.0, unit=ConcentrationUnit.NANOMOLAR)

    def test_concentration__immutability__7b9c6891(self) -> None:
        """Test Concentration is immutable (frozen dataclass)."""
        c = Concentration(value=100.0, unit=ConcentrationUnit.NANOMOLAR)
        with pytest.raises(Exception):  # FrozenInstanceError
            c.value = 200.0  # type: ignore[misc]

    def test_to_unit_same_unit(self) -> None:
        """Test conversion to same unit."""
        c = Concentration(value=100.0, unit=ConcentrationUnit.NANOMOLAR)
        result = c.to_unit(ConcentrationUnit.NANOMOLAR)
        assert result.value == pytest.approx(100.0)
        assert result.unit == ConcentrationUnit.NANOMOLAR

    def test_to_unit_nm_to_um(self) -> None:
        """Test conversion from nM to μM."""
        c = Concentration(value=1000.0, unit=ConcentrationUnit.NANOMOLAR)
        result = c.to_unit(ConcentrationUnit.MICROMOLAR)
        assert result.value == pytest.approx(1.0)
        assert result.unit == ConcentrationUnit.MICROMOLAR

    def test_to_unit_um_to_nm(self) -> None:
        """Test conversion from μM to nM."""
        c = Concentration(value=1.0, unit=ConcentrationUnit.MICROMOLAR)
        result = c.to_unit(ConcentrationUnit.NANOMOLAR)
        assert result.value == pytest.approx(1000.0)
        assert result.unit == ConcentrationUnit.NANOMOLAR

    def test_to_unit_nm_to_pm(self) -> None:
        """Test conversion from nM to pM."""
        c = Concentration(value=1.0, unit=ConcentrationUnit.NANOMOLAR)
        result = c.to_unit(ConcentrationUnit.PICOMOLAR)
        assert result.value == pytest.approx(1000.0)
        assert result.unit == ConcentrationUnit.PICOMOLAR

    def test_to_molar(self) -> None:
        """Test conversion to molar."""
        c = Concentration(value=1000.0, unit=ConcentrationUnit.MILLIMOLAR)
        result = c.to_molar()
        assert result.value == pytest.approx(1.0)
        assert result.unit == ConcentrationUnit.MOLAR

    def test_to_nanomolar(self) -> None:
        """Test conversion to nanomolar."""
        c = Concentration(value=1.0, unit=ConcentrationUnit.MICROMOLAR)
        result = c.to_nanomolar()
        assert result.value == pytest.approx(1000.0)
        assert result.unit == ConcentrationUnit.NANOMOLAR

    def test_molar_value_property(self) -> None:
        """Test molar_value property."""
        c = Concentration(value=100.0, unit=ConcentrationUnit.NANOMOLAR)
        assert c.molar_value == pytest.approx(1e-7)

    def test_from_string_with_space(self) -> None:
        """Test parsing concentration from string with space."""
        c = Concentration.from_string("100 nM")
        assert c.value == pytest.approx(100.0)
        assert c.unit == ConcentrationUnit.NANOMOLAR

    def test_from_string_without_space(self) -> None:
        """Test parsing concentration from string without space."""
        c = Concentration.from_string("0.5μM")
        assert c.value == pytest.approx(0.5)
        assert c.unit == ConcentrationUnit.MICROMOLAR

    def test_from_string_scientific_notation(self) -> None:
        """Test parsing concentration with scientific notation."""
        c = Concentration.from_string("1.5e3 nM")
        assert c.value == pytest.approx(1500.0)
        assert c.unit == ConcentrationUnit.NANOMOLAR

    def test_from_string_negative_exponent(self) -> None:
        """Test parsing concentration with negative exponent."""
        c = Concentration.from_string("1e-6 M")
        assert c.value == pytest.approx(1e-6)
        assert c.unit == ConcentrationUnit.MOLAR

    def test_concentration__invalid_raises__f10a7121(self) -> None:
        """Test invalid string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse concentration"):
            Concentration.from_string("not a concentration")

    def test_str_integer(self) -> None:
        """Test string representation for integer value."""
        c = Concentration(value=100.0, unit=ConcentrationUnit.NANOMOLAR)
        assert str(c) == "100 nM"

    def test_str_float(self) -> None:
        """Test string representation for float value."""
        c = Concentration(value=0.5, unit=ConcentrationUnit.MICROMOLAR)
        assert str(c) == "0.5 μM"

    def test_concentration__equality__8039bd70(self) -> None:
        """Test equality comparison."""
        c1 = Concentration(value=100.0, unit=ConcentrationUnit.NANOMOLAR)
        c2 = Concentration(value=100.0, unit=ConcentrationUnit.NANOMOLAR)
        assert c1 == c2

    def test_concentration__different_values__0da3b7a1(self) -> None:
        """Test inequality for different values."""
        c1 = Concentration(value=100.0, unit=ConcentrationUnit.NANOMOLAR)
        c2 = Concentration(value=200.0, unit=ConcentrationUnit.NANOMOLAR)
        assert c1 != c2

    def test_inequality_different_units(self) -> None:
        """Test inequality for different units (even if equivalent)."""
        c1 = Concentration(value=100.0, unit=ConcentrationUnit.NANOMOLAR)
        c2 = Concentration(value=0.1, unit=ConcentrationUnit.MICROMOLAR)
        # Different representations, so not equal
        assert c1 != c2

    def test_concentration__hash__22d62479(self) -> None:
        """Test hash is consistent with equality."""
        c1 = Concentration(value=100.0, unit=ConcentrationUnit.NANOMOLAR)
        c2 = Concentration(value=100.0, unit=ConcentrationUnit.NANOMOLAR)
        assert hash(c1) == hash(c2)


class TestActivityType:
    """Tests for ActivityType enum."""

    def test_ic50(self) -> None:
        """Test IC50 activity type."""
        assert ActivityType.IC50.value == "IC50"
        assert ActivityType.IC50.is_inhibition_type() is True
        assert ActivityType.IC50.is_binding_type() is False

    def test_ec50(self) -> None:
        """Test EC50 activity type."""
        assert ActivityType.EC50.value == "EC50"
        assert ActivityType.EC50.is_inhibition_type() is False

    def test_ki(self) -> None:
        """Test Ki activity type."""
        assert ActivityType.KI.value == "Ki"
        assert ActivityType.KI.is_inhibition_type() is True
        assert ActivityType.KI.is_binding_type() is True

    def test_kd(self) -> None:
        """Test Kd activity type."""
        assert ActivityType.KD.value == "Kd"
        assert ActivityType.KD.is_binding_type() is True
        assert ActivityType.KD.is_inhibition_type() is False

    def test_from_string_ic50(self) -> None:
        """Test parsing IC50 from string."""
        assert ActivityType.from_string("IC50") == ActivityType.IC50
        assert ActivityType.from_string("ic50") == ActivityType.IC50
        assert ActivityType.from_string("Ic50") == ActivityType.IC50

    def test_from_string_ki(self) -> None:
        """Test parsing Ki from string."""
        assert ActivityType.from_string("Ki") == ActivityType.KI
        assert ActivityType.from_string("ki") == ActivityType.KI
        assert ActivityType.from_string("KI") == ActivityType.KI

    def test_from_string_percent_inhibition(self) -> None:
        """Test parsing % Inhibition from string."""
        assert (
            ActivityType.from_string("% Inhibition") == ActivityType.PERCENT_INHIBITION
        )
        assert (
            ActivityType.from_string("% INHIBITION") == ActivityType.PERCENT_INHIBITION
        )

    def test_activity_type__invalid_raises__0247f8fa(self) -> None:
        """Test invalid type string raises ValueError."""
        with pytest.raises(ValueError, match="Unknown activity type"):
            ActivityType.from_string("UNKNOWN_TYPE")

    def test_all_inhibition_types(self) -> None:
        """Test all inhibition types are identified correctly."""
        inhibition_types = [
            ActivityType.IC50,
            ActivityType.IC90,
            ActivityType.KI,
            ActivityType.INHIBITION,
            ActivityType.PERCENT_INHIBITION,
        ]
        for t in inhibition_types:
            assert t.is_inhibition_type() is True, f"{t} should be inhibition type"

    def test_all_binding_types(self) -> None:
        """Test all binding types are identified correctly."""
        binding_types = [ActivityType.KI, ActivityType.KD]
        for t in binding_types:
            assert t.is_binding_type() is True, f"{t} should be binding type"


class TestPChemblValue:
    """Tests for PChemblValue Value Object."""

    def test_p_chembl_value__creation__717e6346(self) -> None:
        """Test basic creation."""
        p = PChemblValue(value=6.5)
        assert p.value == pytest.approx(6.5)

    def test_p_chembl_value__zero_is_valid__4bc1679c(self) -> None:
        """Test zero pChEMBL value is valid."""
        p = PChemblValue(value=0.0)
        assert p.value == pytest.approx(0.0)

    def test_max_value_is_valid(self) -> None:
        """Test maximum pChEMBL value (14) is valid."""
        p = PChemblValue(value=14.0)
        assert p.value == pytest.approx(14.0)

    def test_p_chembl_value__negative_raises__2ed17162(self) -> None:
        """Test negative pChEMBL value raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            PChemblValue(value=-1.0)

    def test_exceeds_limit_raises(self) -> None:
        """Test pChEMBL value exceeding 14 raises ValueError."""
        with pytest.raises(ValueError, match="exceeds physical limit"):
            PChemblValue(value=15.0)

    def test_p_chembl_value__immutability__df92a25e(self) -> None:
        """Test PChemblValue is immutable (frozen dataclass)."""
        p = PChemblValue(value=6.5)
        with pytest.raises(Exception):  # FrozenInstanceError
            p.value = 7.0  # type: ignore[misc]

    def test_p_chembl_value__to_molar__16e98606(self) -> None:
        """Test conversion to molar concentration."""
        p = PChemblValue(value=6.0)  # pChEMBL 6 = 1 μM
        assert p.to_molar() == pytest.approx(1e-6)

    def test_to_molar_high_potency(self) -> None:
        """Test conversion for high potency compound."""
        p = PChemblValue(value=9.0)  # pChEMBL 9 = 1 nM
        assert p.to_molar() == pytest.approx(1e-9)

    def test_p_chembl_value__to_concentration__309eba67(self) -> None:
        """Test conversion to Concentration object."""
        p = PChemblValue(value=6.0)
        c = p.to_concentration(ConcentrationUnit.MICROMOLAR)
        assert c.value == pytest.approx(1.0)
        assert c.unit == ConcentrationUnit.MICROMOLAR

    def test_to_concentration_default_nm(self) -> None:
        """Test default conversion to nanomolar."""
        p = PChemblValue(value=6.0)
        c = p.to_concentration()  # Default is nM
        assert c.value == pytest.approx(1000.0)
        assert c.unit == ConcentrationUnit.NANOMOLAR

    def test_from_molar(self) -> None:
        """Test creation from molar concentration."""
        p = PChemblValue.from_molar(1e-6)  # 1 μM
        assert p.value == pytest.approx(6.0)

    def test_from_molar_high_potency(self) -> None:
        """Test creation from high potency molar concentration."""
        p = PChemblValue.from_molar(1e-9)  # 1 nM
        assert p.value == pytest.approx(9.0)

    def test_from_molar_zero_raises(self) -> None:
        """Test zero molar concentration raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            PChemblValue.from_molar(0.0)

    def test_from_molar_negative_raises(self) -> None:
        """Test negative molar concentration raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            PChemblValue.from_molar(-1e-6)

    def test_from_concentration(self) -> None:
        """Test creation from Concentration object."""
        c = Concentration(value=1.0, unit=ConcentrationUnit.MICROMOLAR)
        p = PChemblValue.from_concentration(c)
        assert p.value == pytest.approx(6.0)

    def test_p_chembl_value__is_potent__b7cbe8b7(self) -> None:
        """Test is_potent property."""
        assert PChemblValue(value=5.0).is_potent is True
        assert PChemblValue(value=4.9).is_potent is False
        assert PChemblValue(value=7.0).is_potent is True

    def test_p_chembl_value__is_highly_potent__53d165f4(self) -> None:
        """Test is_highly_potent property."""
        assert PChemblValue(value=7.0).is_highly_potent is True
        assert PChemblValue(value=6.9).is_highly_potent is False
        assert PChemblValue(value=9.0).is_highly_potent is True

    def test_p_chembl_value__str__b4844a0d(self) -> None:
        """Test string representation."""
        p = PChemblValue(value=6.543)
        assert str(p) == "6.54"

    def test_p_chembl_value__equality__9fee2a41(self) -> None:
        """Test equality comparison."""
        p1 = PChemblValue(value=6.5)
        p2 = PChemblValue(value=6.5)
        assert p1 == p2

    def test_p_chembl_value__inequality__7eb6f0ac(self) -> None:
        """Test inequality comparison."""
        p1 = PChemblValue(value=6.5)
        p2 = PChemblValue(value=7.0)
        assert p1 != p2

    def test_p_chembl_value__hash__1dfebd72(self) -> None:
        """Test hash is consistent with equality."""
        p1 = PChemblValue(value=6.5)
        p2 = PChemblValue(value=6.5)
        assert hash(p1) == hash(p2)

    def test_p_chembl_value__ordering__ed684335(self) -> None:
        """Test ordering comparison."""
        p1 = PChemblValue(value=6.0)
        p2 = PChemblValue(value=7.0)
        p3 = PChemblValue(value=8.0)
        assert p1 < p2
        assert p2 < p3
        assert not p3 < p1

    def test_can_be_sorted(self) -> None:
        """Test pChEMBL values can be sorted."""
        values = [
            PChemblValue(value=7.0),
            PChemblValue(value=5.0),
            PChemblValue(value=9.0),
        ]
        sorted_values = sorted(values)
        assert sorted_values[0].value == pytest.approx(5.0)
        assert sorted_values[1].value == pytest.approx(7.0)
        assert sorted_values[2].value == pytest.approx(9.0)

    def test_roundtrip_conversion(self) -> None:
        """Test roundtrip conversion pChEMBL -> molar -> pChEMBL."""
        original = PChemblValue(value=6.5)
        molar = original.to_molar()
        recovered = PChemblValue.from_molar(molar)
        assert recovered.value == pytest.approx(original.value)

    def test_roundtrip_concentration(self) -> None:
        """Test roundtrip conversion pChEMBL -> Concentration -> pChEMBL."""
        original = PChemblValue(value=6.5)
        concentration = original.to_concentration()
        recovered = PChemblValue.from_concentration(concentration)
        assert recovered.value == pytest.approx(original.value)
