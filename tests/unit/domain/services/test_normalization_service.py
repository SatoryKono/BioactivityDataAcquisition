"""Unit tests for BioactivityNormalizer facade."""

from __future__ import annotations

import pytest

from bioetl.domain.services.normalization_config import NormalizationConfig
from bioetl.domain.services.normalization_service import (
    BioactivityNormalizer,
    NormalizationResult,
    BioactivityNormalizer,
)
from bioetl.domain.value_objects import Concentration, ConcentrationUnit


class TestBioactivityNormalizerBasic:
    """Basic tests for BioactivityNormalizer."""

    @pytest.fixture
    def service(self) -> BioactivityNormalizer:
        """Create a BioactivityNormalizer instance."""
        return BioactivityNormalizer()

    def test_service_has_subservices(self, service: BioactivityNormalizer) -> None:
        """Test that service has all sub-services."""
        assert service.converter is not None
        assert service.validator is not None
        assert service.aggregator is not None
        assert service.config is not None
        assert BioactivityNormalizer is BioactivityNormalizer


class TestBioactivityNormalizerNormalizeActivity:
    """Tests for normalize_activity method."""

    @pytest.fixture
    def service(self) -> BioactivityNormalizer:
        return BioactivityNormalizer()

    def test_normalize_activity_basic(self, service: BioactivityNormalizer) -> None:
        """Test basic activity normalization."""
        result = service.normalize_activity(100.0, "nM", "IC50")
        assert isinstance(result, NormalizationResult)
        assert result.value == pytest.approx(100.0)
        assert result.unit == "nM"
        assert result.is_valid is True

    def test_normalize_activity_converts_unit(
        self, service: BioactivityNormalizer
    ) -> None:
        """Test that activity is converted to default unit (nM)."""
        result = service.normalize_activity(1.0, "uM", "IC50")
        assert result.value == pytest.approx(1000.0)
        assert result.unit == "nM"

    def test_normalize_activity_calculates_pchembl(
        self, service: BioactivityNormalizer
    ) -> None:
        """Test that pChEMBL is calculated."""
        result = service.normalize_activity(100.0, "nM", "IC50")
        assert result.pchembl is not None
        assert result.pchembl.value == pytest.approx(7.0)

    def test_normalize_activity_potency_flag(
        self, service: BioactivityNormalizer
    ) -> None:
        """Test potency flag based on pChEMBL threshold."""
        # 100 nM = pChEMBL 7.0, threshold is 5.0
        result = service.normalize_activity(100.0, "nM", "IC50")
        assert result.is_potent is True

        # 100 uM = pChEMBL 4.0, below threshold
        result = service.normalize_activity(100.0, "uM", "IC50")
        assert result.is_potent is False

    def test_normalize_activity_invalid_negative(
        self, service: BioactivityNormalizer
    ) -> None:
        """Test that negative values are invalid."""
        result = service.normalize_activity(-100.0, "nM", "IC50")
        assert result.is_valid is False
        assert result.validation_message is not None
        assert "cannot be negative" in result.validation_message

    def test_normalize_activity_skip_validation(
        self, service: BioactivityNormalizer
    ) -> None:
        """Test skipping validation."""
        # Zero would normally be invalid, but with validate=False it passes
        # Note: conversion will still fail for zero since pChEMBL can't be calculated
        result = service.normalize_activity(0.001, "nM", "IC50", validate=False)
        # With validate=False, the concentration below range passes
        assert result.unit == "nM"


class TestBioactivityNormalizerNormalizeToPchembl:
    """Tests for normalize_to_pchembl method."""

    @pytest.fixture
    def service(self) -> BioactivityNormalizer:
        return BioactivityNormalizer()

    def test_normalize_to_pchembl(self, service: BioactivityNormalizer) -> None:
        """Test conversion to pChEMBL value."""
        result = service.normalize_to_pchembl(100.0, "nM")
        assert result is not None
        assert result.value == pytest.approx(7.0)

    def test_normalize_to_pchembl_micromolar(
        self, service: BioactivityNormalizer
    ) -> None:
        """Test pChEMBL from micromolar."""
        result = service.normalize_to_pchembl(1.0, "uM")
        assert result is not None
        # 1 uM = 1e-6 M, -log10 = 6
        assert result.value == pytest.approx(6.0)

    def test_normalize_to_pchembl_invalid_returns_none(
        self, service: BioactivityNormalizer
    ) -> None:
        """Test that invalid values return None."""
        # Zero concentration can't be converted to pChEMBL
        result = service.normalize_to_pchembl(0.0, "nM")
        assert result is None


class TestBioactivityNormalizerNormalizeMultiple:
    """Tests for normalize_multiple method."""

    @pytest.fixture
    def service(self) -> BioactivityNormalizer:
        return BioactivityNormalizer()

    def test_normalize_multiple_aggregates(
        self, service: BioactivityNormalizer
    ) -> None:
        """Test aggregation of multiple values."""
        result = service.normalize_multiple(
            [90.0, 100.0, 110.0], "nM", "IC50", aggregate=True
        )
        assert isinstance(result, NormalizationResult)
        # Median of [90, 100, 110] = 100
        assert result.value == pytest.approx(100.0)
        assert result.is_valid is True

    def test_normalize_multiple_no_aggregate(
        self, service: BioactivityNormalizer
    ) -> None:
        """Test returning individual results without aggregation."""
        results = service.normalize_multiple(
            [90.0, 100.0, 110.0], "nM", "IC50", aggregate=False
        )
        assert isinstance(results, list)
        assert len(results) == 3
        assert all(r.is_valid for r in results)

    def test_normalize_multiple_filters_invalid(
        self, service: BioactivityNormalizer
    ) -> None:
        """Test that invalid values are filtered by default."""
        result = service.normalize_multiple(
            [100.0, -50.0, 200.0],  # -50 is invalid
            "nM",
            "IC50",
            aggregate=True,
            filter_invalid=True,
        )
        # Only valid values [100, 200], median = 150
        assert result.value == pytest.approx(150.0)
        assert result.is_valid is True

    def test_normalize_multiple_all_invalid(
        self, service: BioactivityNormalizer
    ) -> None:
        """Test when all values are invalid."""
        result = service.normalize_multiple(
            [-50.0, -100.0], "nM", "IC50", aggregate=True
        )
        assert result.is_valid is False
        assert "No valid values" in result.validation_message


class TestBioactivityNormalizerNormalizeConcentrations:
    """Tests for normalize_concentrations method."""

    @pytest.fixture
    def service(self) -> BioactivityNormalizer:
        return BioactivityNormalizer()

    def test_normalize_concentrations(self, service: BioactivityNormalizer) -> None:
        """Test normalization of Concentration objects."""
        concs = [
            Concentration(100.0, ConcentrationUnit.NANOMOLAR),
            Concentration(0.1, ConcentrationUnit.MICROMOLAR),  # 100 nM
            Concentration(200.0, ConcentrationUnit.NANOMOLAR),
        ]
        result = service.normalize_concentrations(concs)
        # Values: [100, 100, 200], median = 100
        assert result.value == pytest.approx(100.0)
        assert result.unit == "nM"
        assert result.is_valid is True

    def test_normalize_concentrations_empty(
        self, service: BioactivityNormalizer
    ) -> None:
        """Test with empty concentration list."""
        result = service.normalize_concentrations([])
        assert result.is_valid is False
        assert "No concentrations" in result.validation_message


class TestBioactivityNormalizerPotencyMethods:
    """Tests for potency classification methods."""

    @pytest.fixture
    def service(self) -> BioactivityNormalizer:
        return BioactivityNormalizer()

    def test_is_potent(self, service: BioactivityNormalizer) -> None:
        """Test is_potent method."""
        assert service.is_potent(6.0) is True  # Above 5.0 threshold
        assert service.is_potent(4.0) is False  # Below 5.0 threshold

    def test_is_highly_potent(self, service: BioactivityNormalizer) -> None:
        """Test is_highly_potent method."""
        assert service.is_highly_potent(8.0) is True  # Above 7.0 threshold
        assert service.is_highly_potent(6.0) is False  # Below 7.0 threshold

    def test_classify_potency(self, service: BioactivityNormalizer) -> None:
        """Test potency classification."""
        assert service.classify_potency(3.0) == "inactive"
        assert service.classify_potency(4.5) == "weak"
        assert service.classify_potency(5.5) == "moderate"
        assert service.classify_potency(6.5) == "potent"
        assert service.classify_potency(8.0) == "highly_potent"


class TestBioactivityNormalizerWithConfig:
    """Tests for BioactivityNormalizer with custom config."""

    def test_strict_validation(self) -> None:
        """Test that strict config enables strict validation."""
        config = NormalizationConfig(strict_validation=True)
        service = BioactivityNormalizer(config=config)
        assert service.validator.strict is True

    def test_custom_output_unit(self) -> None:
        """Test custom output unit in config."""
        config = NormalizationConfig(default_output_unit="uM")
        service = BioactivityNormalizer(config=config)
        result = service.normalize_activity(1000.0, "nM", "IC50")
        # 1000 nM = 1 uM
        assert result.value == pytest.approx(1.0)
        assert result.unit == "uM"

    def test_custom_potency_threshold(self) -> None:
        """Test custom potency threshold."""
        config = NormalizationConfig(potency_threshold=6.0)
        service = BioactivityNormalizer(config=config)

        # pChEMBL 5.5 is below new threshold
        result = service.normalize_activity(3162.0, "nM", "IC50")  # ~pChEMBL 5.5
        assert result.is_potent is False

    def test_screening_config(self) -> None:
        """Test with screening configuration."""
        config = NormalizationConfig.for_screening()
        service = BioactivityNormalizer(config=config)
        assert service.config.default_aggregation_method == "mean"
        assert service.config.potency_threshold == pytest.approx(4.0)

    def test_medicinal_chemistry_config(self) -> None:
        """Test with medicinal chemistry configuration."""
        config = NormalizationConfig.for_medicinal_chemistry()
        service = BioactivityNormalizer(config=config)
        assert service.config.default_aggregation_method == "median"
        assert service.config.strict_validation is True
        assert service.validator.strict is True


class TestNormalizationResult:
    """Tests for NormalizationResult dataclass."""

    def test_result_fields(self) -> None:
        """Test that result has all expected fields."""
        result = NormalizationResult(
            value=100.0,
            unit="nM",
        )
        assert result.value == pytest.approx(100.0)
        assert result.unit == "nM"
        assert result.pchembl is None
        assert result.is_valid is True
        assert result.validation_message is None
        assert result.is_potent is False

    def test_result_with_all_fields(self) -> None:
        """Test result with all fields populated."""
        from bioetl.domain.value_objects import PChemblValue

        result = NormalizationResult(
            value=100.0,
            unit="nM",
            pchembl=PChemblValue(7.0),
            is_valid=True,
            validation_message=None,
            is_potent=True,
        )
        assert result.pchembl.value == pytest.approx(7.0)
        assert result.is_potent is True
