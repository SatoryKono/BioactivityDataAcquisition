"""Focused tests for structural policy value coercion."""

from __future__ import annotations

import math

import pytest

from bioetl.application.core.base_transformer._structural_policy_coercion import (
    coerce_value,
)
from bioetl.application.core.base_transformer._structural_policy_types import (
    LogicalType,
    StructuralFieldSpec,
)
from bioetl.application.core.base_transformer.field_policy import FieldCoercionPolicy

pytestmark = pytest.mark.unit


def _contract(
    logical_type: LogicalType,
    *,
    coercion_policy: FieldCoercionPolicy = "default",
    true_values: tuple[str, ...] = (),
    false_values: tuple[str, ...] = (),
) -> StructuralFieldSpec:
    return StructuralFieldSpec(
        field_name="field",
        logical_type=logical_type,
        physical_type="string",
        nullable=False,
        optional=False,
        optional_sources=(),
        coercion_policy=coercion_policy,
        boolean_true_values=true_values,
        boolean_false_values=false_values,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (7, 7),
        (7.0, 7),
        (" 7 ", 7),
        ("7.0", 7),
        (True, None),
        (7.5, None),
        (math.inf, None),
        ("7.5", None),
        ("", None),
        ("not-an-int", None),
    ],
)
def test_integer_coercion_accepts_only_integral_values(
    value: object,
    expected: int | None,
) -> None:
    assert coerce_value(value, _contract("integer")) == expected


def test_integer_coercion_can_disable_string_inputs() -> None:
    assert (
        coerce_value("7", _contract("integer", coercion_policy="no_string_coercion"))
        is None
    )


def test_float_coercion_can_disable_string_inputs() -> None:
    assert (
        coerce_value("2.5", _contract("float", coercion_policy="no_string_coercion"))
        is None
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (2, 2.0),
        (2.5, 2.5),
        (" 2.5 ", 2.5),
        (False, None),
        (math.nan, None),
        ("nan", None),
        ("", None),
        ("not-a-float", None),
    ],
)
def test_float_coercion_rejects_bool_empty_and_non_finite_values(
    value: object,
    expected: float | None,
) -> None:
    assert coerce_value(value, _contract("float")) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        (2, None),
        (" yes ", True),
        ("No", False),
        ("maybe", None),
    ],
)
def test_boolean_coercion_uses_default_vocabularies(
    value: object,
    expected: bool | None,
) -> None:
    assert coerce_value(value, _contract("boolean")) is expected


def test_boolean_coercion_honors_custom_vocabularies() -> None:
    contract = _contract("boolean", true_values=("pass",), false_values=("reject",))

    assert coerce_value("pass", contract) is True
    assert coerce_value("reject", contract) is False
    assert coerce_value("yes", contract) is None


def test_boolean_coercion_can_disable_string_inputs() -> None:
    assert (
        coerce_value("yes", _contract("boolean", coercion_policy="no_string_coercion"))
        is None
    )


def test_unknown_logical_type_returns_original_value() -> None:
    value = {"raw": "value"}

    assert coerce_value(value, _contract("unknown")) is value
