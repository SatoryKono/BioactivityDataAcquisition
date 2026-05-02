"""Unit tests for NormalizationConfig."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.normalization_config import (
    ConcentrationRangeConfig,
    NormalizationConfig,
    PChemblRangeConfig,
)


class TestConcentrationRangeConfig:
    """Tests for ConcentrationRangeConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ConcentrationRangeConfig()
        assert config.min_molar == pytest.approx(1e-15)
        assert config.max_molar == pytest.approx(1e-1)

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = ConcentrationRangeConfig(min_molar=1e-12, max_molar=1e-3)
        assert config.min_molar == pytest.approx(1e-12)
        assert config.max_molar == pytest.approx(1e-3)

    def test_invalid_min_molar_raises(self) -> None:
        """Test that non-positive min_molar raises ValueError."""
        with pytest.raises(ValueError, match="min_molar must be positive"):
            ConcentrationRangeConfig(min_molar=0)

    def test_invalid_max_molar_raises(self) -> None:
        """Test that non-positive max_molar raises ValueError."""
        with pytest.raises(ValueError, match="max_molar must be positive"):
            ConcentrationRangeConfig(max_molar=-1e-6)

    def test_invalid_range_raises(self) -> None:
        """Test that min >= max raises ValueError."""
        with pytest.raises(ValueError, match="must be less than"):
            ConcentrationRangeConfig(min_molar=1e-3, max_molar=1e-6)


class TestPChemblRangeConfig:
    """Tests for PChemblRangeConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = PChemblRangeConfig()
        assert config.min_value == pytest.approx(0.0)
        assert config.max_value == pytest.approx(14.0)
        assert config.typical_min == pytest.approx(2.0)
        assert config.typical_max == pytest.approx(12.0)

    def test_invalid_min_value_raises(self) -> None:
        """Test that negative min_value raises ValueError."""
        with pytest.raises(ValueError, match="min_value cannot be negative"):
            PChemblRangeConfig(min_value=-1.0)

    def test_invalid_max_value_raises(self) -> None:
        """Test that max_value > 15 raises ValueError."""
        with pytest.raises(ValueError, match="exceeds physical limit"):
            PChemblRangeConfig(max_value=16.0)

    def test_invalid_range_raises(self) -> None:
        """Test that min >= max raises ValueError."""
        with pytest.raises(ValueError, match="must be less than"):
            PChemblRangeConfig(min_value=10.0, max_value=5.0)

    def test_invalid_typical_range_raises(self) -> None:
        """Test that typical_min >= typical_max raises ValueError."""
        with pytest.raises(ValueError, match="typical_min must be less than"):
            PChemblRangeConfig(typical_min=10.0, typical_max=5.0)


class TestNormalizationConfig:
    """Tests for NormalizationConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = NormalizationConfig()
        assert config.default_output_unit == "nM"
        assert config.strict_validation is False
        assert config.default_aggregation_method == "median"
        assert config.potency_threshold == pytest.approx(5.0)
        assert config.high_potency_threshold == pytest.approx(7.0)

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = NormalizationConfig(
            default_output_unit="µM",
            strict_validation=True,
            default_aggregation_method="mean",
            potency_threshold=6.0,
            high_potency_threshold=8.0,
        )
        assert config.default_output_unit == "µM"
        assert config.strict_validation is True
        assert config.default_aggregation_method == "mean"
        assert config.potency_threshold == pytest.approx(6.0)
        assert config.high_potency_threshold == pytest.approx(8.0)

    def test_negative_potency_threshold_raises(self) -> None:
        """Test that negative potency threshold raises ValueError."""
        with pytest.raises(ValueError, match="potency_threshold cannot be negative"):
            NormalizationConfig(potency_threshold=-1.0)

    def test_invalid_threshold_order_raises(self) -> None:
        """Test that high < potency threshold raises ValueError."""
        with pytest.raises(ValueError, match="must be >= potency_threshold"):
            NormalizationConfig(potency_threshold=7.0, high_potency_threshold=5.0)

    def test_invalid_aggregation_method_raises(self) -> None:
        """Test that invalid aggregation method raises ValueError."""
        with pytest.raises(ValueError, match="Invalid aggregation method"):
            NormalizationConfig(default_aggregation_method="invalid")  # type: ignore

    def test_immutability(self) -> None:
        """Test that config is immutable (frozen dataclass)."""
        config = NormalizationConfig()
        with pytest.raises(AttributeError):
            config.strict_validation = True  # type: ignore


class TestNormalizationConfigFactories:
    """Tests for NormalizationConfig factory methods."""

    def test_strict_factory(self) -> None:
        """Test strict() factory method."""
        config = NormalizationConfig.strict()
        assert config.strict_validation is True

    def test_for_screening_factory(self) -> None:
        """Test for_screening() factory method."""
        config = NormalizationConfig.for_screening()
        assert config.default_aggregation_method == "mean"
        assert config.strict_validation is False
        assert config.potency_threshold == pytest.approx(4.0)

    def test_for_medicinal_chemistry_factory(self) -> None:
        """Test for_medicinal_chemistry() factory method."""
        config = NormalizationConfig.for_medicinal_chemistry()
        assert config.default_aggregation_method == "median"
        assert config.strict_validation is True
        assert config.potency_threshold == pytest.approx(6.0)
        assert config.high_potency_threshold == pytest.approx(8.0)
