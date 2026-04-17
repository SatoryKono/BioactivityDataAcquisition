"""Unit tests for molecular descriptor value objects."""

from __future__ import annotations

import pytest

from bioetl.domain.value_objects.molecular_descriptors import (
    HeavyAtomCount,
    HydrogenBondCount,
    LogP,
    PolarSurfaceArea,
    RotatableBondCount,
)


@pytest.mark.unit
class TestCoerceHelpers:
    """Indirectly test _coerce_int and _coerce_float via VO creation."""

    def test_hydrogen_bond_count_from_int(self) -> None:
        """Test HydrogenBondCount accepts integer."""
        hbc = HydrogenBondCount(5)
        assert hbc.value == 5

    def test_hydrogen_bond_count_from_float(self) -> None:
        """Test HydrogenBondCount accepts float (coerces to int)."""
        hbc = HydrogenBondCount(3.0)
        assert hbc.value == 3

    def test_hydrogen_bond_count_from_string(self) -> None:
        """Test HydrogenBondCount accepts numeric string."""
        hbc = HydrogenBondCount("7")
        assert hbc.value == 7

    def test_bool_raises_value_error(self) -> None:
        """Test that bool input raises ValueError (prevents bool→int coercion)."""
        with pytest.raises(ValueError):
            HydrogenBondCount(True)

    def test_infinite_float_raises_value_error(self) -> None:
        """Test that infinite float raises ValueError."""
        with pytest.raises(ValueError):
            HydrogenBondCount(float("inf"))

    def test_nan_float_raises_value_error(self) -> None:
        """Test that NaN raises ValueError in LogP."""
        with pytest.raises(ValueError):
            LogP(float("nan"))

    def test_non_numeric_string_raises_value_error(self) -> None:
        """Test that non-numeric string raises ValueError."""
        with pytest.raises(ValueError):
            HydrogenBondCount("not_a_number")

    def test_logp_bool_raises_value_error(self) -> None:
        """Test that bool raises ValueError for float coercion too."""
        with pytest.raises(ValueError):
            LogP(True)

    def test_logp_from_string_raises_value_error(self) -> None:
        """Test that invalid string raises ValueError for LogP."""
        with pytest.raises(ValueError):
            LogP("invalid")


@pytest.mark.unit
class TestHydrogenBondCount:
    """Tests for HydrogenBondCount value object."""

    def test_valid_zero(self) -> None:
        """Test zero is valid."""
        hbc = HydrogenBondCount(0)
        assert hbc.value == 0

    def test_valid_positive(self) -> None:
        """Test positive value is valid."""
        hbc = HydrogenBondCount(10)
        assert hbc.value == 10

    def test_out_of_range_raises(self) -> None:
        """Test out-of-range value raises ValueError."""
        with pytest.raises(ValueError, match="outside"):
            HydrogenBondCount(10000)  # Way beyond max

    def test_from_raw_none_returns_none(self) -> None:
        """Test from_raw(None) returns None."""
        assert HydrogenBondCount.from_raw(None) is None

    def test_from_raw_valid_returns_instance(self) -> None:
        """Test from_raw with valid value returns instance."""
        result = HydrogenBondCount.from_raw(5)
        assert result is not None
        assert result.value == 5

    def test_from_raw_invalid_returns_none(self) -> None:
        """Test from_raw with invalid value returns None (no exception)."""
        result = HydrogenBondCount.from_raw("not_a_number")
        assert result is None

    def test_from_raw_out_of_range_returns_none(self) -> None:
        """Test from_raw with out-of-range value returns None."""
        result = HydrogenBondCount.from_raw(99999)
        assert result is None


@pytest.mark.unit
class TestRotatableBondCount:
    """Tests for RotatableBondCount value object."""

    def test_valid_creation(self) -> None:
        """Test valid creation."""
        rbc = RotatableBondCount(5)
        assert rbc.value == 5

    def test_from_raw_none_returns_none(self) -> None:
        """Test from_raw(None) returns None."""
        assert RotatableBondCount.from_raw(None) is None

    def test_from_raw_valid(self) -> None:
        """Test from_raw with valid value."""
        result = RotatableBondCount.from_raw(3)
        assert result is not None
        assert result.value == 3

    def test_from_raw_out_of_range_returns_none(self) -> None:
        """Test from_raw with out-of-range value returns None."""
        result = RotatableBondCount.from_raw(99999)
        assert result is None


@pytest.mark.unit
class TestHeavyAtomCount:
    """Tests for HeavyAtomCount value object."""

    def test_valid_creation(self) -> None:
        """Test valid creation."""
        hac = HeavyAtomCount(20)
        assert hac.value == 20

    def test_from_raw_none_returns_none(self) -> None:
        """Test from_raw(None) returns None."""
        assert HeavyAtomCount.from_raw(None) is None

    def test_from_raw_valid(self) -> None:
        """Test from_raw with valid value."""
        result = HeavyAtomCount.from_raw(15)
        assert result is not None
        assert result.value == 15

    def test_from_raw_string(self) -> None:
        """Test from_raw with numeric string."""
        result = HeavyAtomCount.from_raw("10")
        assert result is not None
        assert result.value == 10


@pytest.mark.unit
class TestPolarSurfaceArea:
    """Tests for PolarSurfaceArea value object."""

    def test_valid_zero(self) -> None:
        """Test zero is valid for PSA."""
        psa = PolarSurfaceArea(0.0)
        assert psa.value == pytest.approx(0.0)

    def test_valid_positive(self) -> None:
        """Test positive value is valid."""
        psa = PolarSurfaceArea(75.5)
        assert psa.value == pytest.approx(75.5)

    def test_out_of_range_raises(self) -> None:
        """Test out-of-range value raises ValueError."""
        with pytest.raises(ValueError, match="outside"):
            PolarSurfaceArea(99999.0)

    def test_from_raw_none_returns_none(self) -> None:
        """Test from_raw(None) returns None."""
        assert PolarSurfaceArea.from_raw(None) is None

    def test_from_raw_valid(self) -> None:
        """Test from_raw with valid float."""
        result = PolarSurfaceArea.from_raw(45.2)
        assert result is not None
        assert result.value == pytest.approx(45.2)

    def test_from_raw_invalid_returns_none(self) -> None:
        """Test from_raw with out-of-range value returns None."""
        result = PolarSurfaceArea.from_raw(999999.0)
        assert result is None


@pytest.mark.unit
class TestLogP:
    """Tests for LogP value object."""

    def test_valid_negative(self) -> None:
        """Test negative LogP is valid."""
        logp = LogP(-2.5)
        assert logp.value == pytest.approx(-2.5)

    def test_valid_positive(self) -> None:
        """Test positive LogP is valid."""
        logp = LogP(3.14)
        assert logp.value == pytest.approx(3.14)

    def test_valid_zero(self) -> None:
        """Test zero LogP is valid."""
        logp = LogP(0.0)
        assert logp.value == pytest.approx(0.0)

    def test_out_of_range_raises(self) -> None:
        """Test out-of-range LogP raises ValueError."""
        with pytest.raises(ValueError, match="outside"):
            LogP(9999.0)

    def test_from_raw_none_returns_none(self) -> None:
        """Test from_raw(None) returns None."""
        assert LogP.from_raw(None) is None

    def test_from_raw_valid(self) -> None:
        """Test from_raw with valid value."""
        result = LogP.from_raw(1.5)
        assert result is not None
        assert result.value == pytest.approx(1.5)

    def test_from_raw_string_valid(self) -> None:
        """Test from_raw with numeric string."""
        result = LogP.from_raw("2.3")
        assert result is not None

    def test_from_raw_out_of_range_returns_none(self) -> None:
        """Test from_raw with out-of-range value returns None."""
        result = LogP.from_raw(999999.0)
        assert result is None

    def test_from_raw_nan_returns_none(self) -> None:
        """Test from_raw with NaN returns None."""
        result = LogP.from_raw(float("nan"))
        assert result is None

    def test_from_raw_inf_returns_none(self) -> None:
        """Test from_raw with infinite returns None."""
        result = LogP.from_raw(float("inf"))
        assert result is None
