"""Unit tests for bioactivity value validation behavior."""

from __future__ import annotations

import math

import pytest

from bioetl.domain.behavior.value_validator import ValueValidator
from bioetl.domain.value_objects import ActivityType

pytestmark = pytest.mark.unit


def test_validate_concentration_reports_basic_and_unit_errors() -> None:
    validator = ValueValidator()

    assert validator.validate_concentration(-1.0, "nM") == (
        False,
        "Concentration cannot be negative: -1.0",
    )
    assert validator.validate_concentration(0.0, "nM") == (
        False,
        "Concentration cannot be zero",
    )
    assert validator.validate_concentration(10.0, "unknown") == (
        False,
        "Unknown concentration unit: unknown",
    )


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_validate_concentration_rejects_non_finite_values(value: float) -> None:
    valid, error = ValueValidator().validate_concentration(value, "nM")

    assert valid is False
    assert error == f"Concentration must be finite: {value}"


def test_validate_concentration_honors_custom_range_and_aliases() -> None:
    validator = ValueValidator()
    validator.set_concentration_range("nanomolar", 1.0, 10.0)

    assert validator.validate_concentration(5.0, "nM") == (True, None)
    assert validator.validate_concentration(0.5, "nM")[1] == (
        "Concentration 0.5 nM below minimum (1.0 nM)"
    )
    assert validator.validate_concentration(20.0, "nM")[1] == (
        "Concentration 20.0 nM exceeds maximum (10.0 nM)"
    )


def test_set_concentration_range_rejects_inverted_bounds() -> None:
    with pytest.raises(ValueError, match="min_value must be less than max_value"):
        ValueValidator().set_concentration_range("nM", 10.0, 10.0)


def test_validate_pchembl_covers_absolute_and_strict_typical_ranges() -> None:
    validator = ValueValidator()
    strict_validator = ValueValidator(strict=True)

    assert validator.validate_pchembl(7.5) == (True, None)
    assert validator.validate_pchembl(-0.1)[1] == (
        "pChEMBL value cannot be negative: -0.10"
    )
    assert validator.validate_pchembl(15.0)[1] == (
        "pChEMBL value 15.00 exceeds maximum 14.00"
    )
    assert strict_validator.validate_pchembl(1.5)[1] == (
        "pChEMBL value 1.50 below typical minimum 2.00 (very weak activity)"
    )
    assert strict_validator.validate_pchembl(13.0)[1] == (
        "pChEMBL value 13.00 exceeds typical maximum 12.00 (unusually potent)"
    )


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_validate_pchembl_rejects_non_finite_values(value: float) -> None:
    valid, error = ValueValidator().validate_pchembl(value)

    assert valid is False
    assert error == f"pChEMBL value must be finite: {value}"


def test_validate_activity_value_routes_by_unit_type_and_percent_range() -> None:
    validator = ValueValidator()

    assert validator.validate_activity_value(50.0, ActivityType.PERCENT_INHIBITION) == (
        True,
        None,
    )
    assert validator.validate_activity_value(
        150.0, ActivityType.PERCENT_INHIBITION
    ) == (False, "Percent inhibition must be 0-100, got 150.0")
    assert validator.validate_activity_value(-1.0, "IC50") == (
        False,
        "Activity value cannot be negative: -1.0",
    )
    assert validator.validate_activity_value(10.0, "IC50", "nM") == (True, None)
    assert validator.validate_activity_value(10.0, "UNKNOWN_TYPE") == (True, None)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_validate_activity_value_rejects_non_finite_values(value: float) -> None:
    valid, error = ValueValidator().validate_activity_value(value, "IC50")

    assert valid is False
    assert error == f"Activity value must be finite: {value}"


def test_potency_helpers_use_configurable_thresholds() -> None:
    validator = ValueValidator()

    assert validator.is_potent(5.0)
    assert not validator.is_potent(4.99)
    assert validator.is_highly_potent(7.0)
    assert not validator.is_highly_potent(6.99)
    assert validator.is_potent(6.0, threshold=6.0)
