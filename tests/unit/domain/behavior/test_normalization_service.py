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
"""Unit tests for bioactivity normalization service."""

from __future__ import annotations

import math

import pytest

from bioetl.domain.behavior.normalization_config import NormalizationConfig
from bioetl.domain.behavior.normalization_service import BioactivityNormalizer
from bioetl.domain.value_objects import Concentration, ConcentrationUnit

pytestmark = pytest.mark.unit


def test_normalize_activity_converts_to_default_unit_and_computes_pchembl() -> None:
    normalizer = BioactivityNormalizer()

    result = normalizer.normalize_activity(1.0, "uM", "IC50")

    assert result.is_valid is True
    assert result.value == pytest.approx(1000.0)
    assert result.unit == "nM"
    assert result.pchembl is not None
    assert result.pchembl.value == pytest.approx(6.0)
    assert result.is_potent is True


def test_normalize_activity_returns_invalid_result_for_validation_or_conversion_error() -> (
    None
):
    normalizer = BioactivityNormalizer()

    invalid_value = normalizer.normalize_activity(0.0, "nM", "IC50")
    invalid_unit = normalizer.normalize_activity(
        10.0, "bad-unit", "IC50", validate=False
    )

    assert invalid_value.is_valid is False
    assert invalid_value.validation_message == "Concentration cannot be zero"
    assert invalid_unit.is_valid is False
    assert "Unknown concentration unit" in str(invalid_unit.validation_message)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_normalize_activity_rejects_non_finite_values(value: float) -> None:
    result = BioactivityNormalizer().normalize_activity(value, "nM", "IC50")

    assert result.is_valid is False
    assert result.validation_message == f"Concentration must be finite: {value}"


def test_normalize_to_pchembl_returns_none_for_invalid_or_out_of_range_values() -> None:
    normalizer = BioactivityNormalizer(config=NormalizationConfig.strict())

    assert normalizer.normalize_to_pchembl(100.0, "nM") is not None
    assert normalizer.normalize_to_pchembl(1e20, "nM") is None
    assert normalizer.normalize_to_pchembl(10.0, "bad-unit") is None


def test_classify_potency_uses_configured_thresholds() -> None:
    normalizer = BioactivityNormalizer(
        config=NormalizationConfig(
            potency_threshold=5.5,
            high_potency_threshold=7.5,
        )
    )

    assert normalizer.classify_potency(3.9) == "inactive"
    assert normalizer.classify_potency(5.0) == "weak"
    assert normalizer.classify_potency(5.7) == "moderate"
    assert normalizer.classify_potency(7.0) == "potent"
    assert normalizer.classify_potency(7.5) == "highly_potent"
    assert normalizer.is_potent(5.5)
    assert normalizer.is_highly_potent(7.5)


def test_normalize_multiple_can_return_individual_or_aggregated_results() -> None:
    normalizer = BioactivityNormalizer()

    individual = normalizer.normalize_multiple(
        [100.0, 1000.0],
        "nM",
        "IC50",
        aggregate=False,
    )
    aggregated = normalizer.normalize_multiple(
        [100.0, 1000.0],
        "nM",
        "IC50",
        aggregate=True,
    )

    assert isinstance(individual, list)
    assert [item.value for item in individual] == pytest.approx([100.0, 1000.0])
    assert not isinstance(aggregated, list)
    assert aggregated.is_valid is True
    assert aggregated.unit == "nM"


def test_normalize_multiple_reports_no_valid_values() -> None:
    result = BioactivityNormalizer().normalize_multiple(
        [0.0, -1.0],
        "nM",
        "IC50",
        aggregate=True,
        filter_invalid=True,
    )

    assert result.is_valid is False
    assert result.validation_message == "No valid values to aggregate"


def test_normalize_concentrations_handles_empty_and_valid_inputs() -> None:
    normalizer = BioactivityNormalizer()

    empty = normalizer.normalize_concentrations([])
    valid = normalizer.normalize_concentrations(
        [
            Concentration(100.0, ConcentrationUnit.NANOMOLAR),
            Concentration(1000.0, ConcentrationUnit.NANOMOLAR),
        ]
    )

    assert empty.is_valid is False
    assert empty.validation_message == "No concentrations to normalize"
    assert valid.is_valid is True
    assert valid.unit == "nM"
    assert valid.pchembl is not None


def test_post_init_propagates_strict_validation_to_validator() -> None:
    normalizer = BioactivityNormalizer(config=NormalizationConfig.strict())

    assert normalizer.validator.strict is True
