"""Unit tests for ValueValidator service."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.value_validator import (
    PCHEMBL_MAX,
    PCHEMBL_MIN,
    ValueValidator,
)
from bioetl.domain.value_objects import ActivityType

pytestmark = pytest.mark.unit


class TestValueValidatorConcentration:
    """Tests for concentration validation."""

    @pytest.fixture
    def validator(self) -> ValueValidator:
        """Create a ValueValidator instance."""
        return ValueValidator()

    def test_valid_concentration_nm(self, validator: ValueValidator) -> None:
        """Test valid nanomolar concentration."""
        is_valid, error = validator.validate_concentration(100.0, "nM")
        assert is_valid is True
        assert error is None

    def test_valid_concentration_um(self, validator: ValueValidator) -> None:
        """Test valid micromolar concentration."""
        is_valid, error = validator.validate_concentration(1.0, "µM")
        assert is_valid is True
        assert error is None

    def test_valid_concentration_um_alias(self, validator: ValueValidator) -> None:
        """Test uM alias for µM."""
        is_valid, error = validator.validate_concentration(1.0, "uM")
        assert is_valid is True
        assert error is None

    def test_negative_concentration_invalid(self, validator: ValueValidator) -> None:
        """Test that negative concentration is invalid."""
        is_valid, error = validator.validate_concentration(-1.0, "nM")
        assert is_valid is False
        assert error is not None
        assert "cannot be negative" in error

    def test_zero_concentration_invalid(self, validator: ValueValidator) -> None:
        """Test that zero concentration is invalid."""
        is_valid, error = validator.validate_concentration(0.0, "nM")
        assert is_valid is False
        assert error is not None
        assert "cannot be zero" in error

    def test_unknown_unit_invalid(self, validator: ValueValidator) -> None:
        """Test that unknown unit is invalid."""
        is_valid, error = validator.validate_concentration(100.0, "unknown")
        assert is_valid is False
        assert error is not None
        assert "Unknown concentration unit" in error

    def test_concentration_below_minimum(self, validator: ValueValidator) -> None:
        """Test concentration below minimum range."""
        # nM range minimum is 1e-6
        is_valid, error = validator.validate_concentration(1e-10, "nM")
        assert is_valid is False
        assert error is not None
        assert "below minimum" in error

    def test_concentration_above_maximum(self, validator: ValueValidator) -> None:
        """Test concentration above maximum range."""
        # nM range maximum is 1e8
        is_valid, error = validator.validate_concentration(1e12, "nM")
        assert is_valid is False
        assert error is not None
        assert "exceeds maximum" in error


class TestValueValidatorPChembl:
    """Tests for pChEMBL validation."""

    @pytest.fixture
    def validator(self) -> ValueValidator:
        return ValueValidator()

    def test_valid_pchembl(self, validator: ValueValidator) -> None:
        """Test valid pChEMBL value."""
        is_valid, error = validator.validate_pchembl(7.5)
        assert is_valid is True
        assert error is None

    def test_pchembl_at_minimum(self, validator: ValueValidator) -> None:
        """Test pChEMBL at minimum boundary."""
        is_valid, error = validator.validate_pchembl(PCHEMBL_MIN)
        assert is_valid is True
        assert error is None

    def test_pchembl_at_maximum(self, validator: ValueValidator) -> None:
        """Test pChEMBL at maximum boundary."""
        is_valid, error = validator.validate_pchembl(PCHEMBL_MAX)
        assert is_valid is True
        assert error is None

    def test_negative_pchembl_invalid(self, validator: ValueValidator) -> None:
        """Test that negative pChEMBL is invalid."""
        is_valid, error = validator.validate_pchembl(-1.0)
        assert is_valid is False
        assert error is not None
        assert "cannot be negative" in error

    def test_pchembl_exceeds_maximum(self, validator: ValueValidator) -> None:
        """Test pChEMBL exceeding maximum."""
        is_valid, error = validator.validate_pchembl(15.0)
        assert is_valid is False
        assert error is not None
        assert "exceeds maximum" in error


class TestValueValidatorStrict:
    """Tests for strict validation mode."""

    def test_strict_rejects_low_pchembl(self) -> None:
        """Test that strict mode rejects very low pChEMBL values."""
        validator = ValueValidator(strict=True)
        is_valid, error = validator.validate_pchembl(1.0)
        assert is_valid is False
        assert error is not None
        assert "below typical minimum" in error

    def test_strict_rejects_high_pchembl(self) -> None:
        """Test that strict mode rejects unusually high pChEMBL values."""
        validator = ValueValidator(strict=True)
        is_valid, error = validator.validate_pchembl(13.0)
        assert is_valid is False
        assert error is not None
        assert "exceeds typical maximum" in error

    def test_strict_accepts_typical_pchembl(self) -> None:
        """Test that strict mode accepts typical pChEMBL values."""
        validator = ValueValidator(strict=True)
        is_valid, error = validator.validate_pchembl(7.0)
        assert is_valid is True
        assert error is None


class TestValueValidatorActivity:
    """Tests for activity value validation."""

    @pytest.fixture
    def validator(self) -> ValueValidator:
        return ValueValidator()

    def test_valid_activity_with_unit(self, validator: ValueValidator) -> None:
        """Test valid activity with unit delegates to concentration validation."""
        is_valid, error = validator.validate_activity_value(100.0, "IC50", "nM")
        assert is_valid is True
        assert error is None

    def test_negative_activity_invalid(self, validator: ValueValidator) -> None:
        """Test that negative activity is invalid."""
        is_valid, error = validator.validate_activity_value(-50.0, "IC50")
        assert is_valid is False
        assert error is not None
        assert "cannot be negative" in error

    def test_valid_activity_type_enum(self, validator: ValueValidator) -> None:
        """Test validation with ActivityType enum."""
        is_valid, error = validator.validate_activity_value(
            100.0, ActivityType.IC50, "nM"
        )
        assert is_valid is True
        assert error is None

    def test_percent_inhibition_valid_range(self, validator: ValueValidator) -> None:
        """Test valid percent inhibition."""
        is_valid, error = validator.validate_activity_value(
            50.0, ActivityType.PERCENT_INHIBITION
        )
        assert is_valid is True
        assert error is None

    def test_percent_inhibition_over_100_invalid(
        self, validator: ValueValidator
    ) -> None:
        """Test that percent inhibition > 100 is invalid."""
        is_valid, error = validator.validate_activity_value(
            150.0, ActivityType.PERCENT_INHIBITION
        )
        assert is_valid is False
        assert error is not None
        assert "must be 0-100" in error

    def test_unknown_activity_type_allowed(self, validator: ValueValidator) -> None:
        """Test that unknown activity types are allowed with basic validation."""
        is_valid, error = validator.validate_activity_value(100.0, "UNKNOWN_TYPE")
        assert is_valid is True
        assert error is None


class TestValueValidatorPotency:
    """Tests for potency classification."""

    @pytest.fixture
    def validator(self) -> ValueValidator:
        return ValueValidator()

    def test_is_potent_above_threshold(self, validator: ValueValidator) -> None:
        """Test is_potent returns True above threshold."""
        assert validator.is_potent(6.0, threshold=5.0) is True

    def test_is_potent_below_threshold(self, validator: ValueValidator) -> None:
        """Test is_potent returns False below threshold."""
        assert validator.is_potent(4.0, threshold=5.0) is False

    def test_is_potent_at_threshold(self, validator: ValueValidator) -> None:
        """Test is_potent returns True at threshold."""
        assert validator.is_potent(5.0, threshold=5.0) is True

    def test_validator_potency__is_highly_potent__737d1a6a(self, validator: ValueValidator) -> None:
        """Test is_highly_potent classification."""
        assert validator.is_highly_potent(8.0, threshold=7.0) is True
        assert validator.is_highly_potent(6.0, threshold=7.0) is False


class TestValueValidatorCustomRanges:
    """Tests for custom concentration ranges."""

    def test_set_concentration_range(self) -> None:
        """Test setting custom concentration range."""
        validator = ValueValidator()
        validator.set_concentration_range("nM", 1.0, 1000.0)

        # Value within custom range should be valid
        is_valid, error = validator.validate_concentration(100.0, "nM")
        assert is_valid is True

        # Value outside custom range should be invalid
        is_valid, error = validator.validate_concentration(0.5, "nM")
        assert is_valid is False
        assert "below minimum" in error

    def test_set_concentration_range_invalid(self) -> None:
        """Test that invalid range raises ValueError."""
        validator = ValueValidator()
        with pytest.raises(ValueError, match="must be less than"):
            validator.set_concentration_range("nM", 1000.0, 100.0)
