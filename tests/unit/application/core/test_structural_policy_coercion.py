# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Focused tests for structural policy value coercion."""

from __future__ import annotations

import math

import pytest

from bioetl.application.core.base_transformer._structural_policy_coercion import (
    coerce_value,
)
from bioetl.application.core.base_transformer._structural_policy_contracts import (
    resolve_logical_type,
)
from bioetl.application.core.base_transformer._structural_policy_events import (
    preview_value,
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


def test_boolean_coercion_lowercases_configured_vocabularies() -> None:
    contract = _contract(
        "boolean", true_values=("Yes", "ON"), false_values=("No", "OFF")
    )

    assert coerce_value("YES", contract) is True
    assert coerce_value("on", contract) is True
    assert coerce_value("No", contract) is False
    assert coerce_value("off", contract) is False


def test_boolean_coercion_can_disable_string_inputs() -> None:
    assert (
        coerce_value("yes", _contract("boolean", coercion_policy="no_string_coercion"))
        is None
    )


def test_unknown_logical_type_returns_original_value() -> None:
    value = {"raw": "value"}

    assert coerce_value(value, _contract("unknown")) is value


@pytest.mark.parametrize(
    ("physical_type", "expected"),
    [
        ("UInt64", "integer"),
        ("uint32[pyarrow]", "integer"),
        ("Float64", "float"),
        ("double", "float"),
        ("decimal128(10, 2)", "float"),
        ("datetime64[ns]", "string"),
        ("Date", "string"),
        ("timestamp[ns]", "string"),
        ("category", "string"),
        ("object", "unknown"),
        ("custom_timestamp", "unknown"),
        ("customstring", "unknown"),
        ("notafloat", "unknown"),
    ],
)
def test_resolve_logical_type_classifies_extended_pandera_dtypes(
    physical_type: str,
    expected: str,
) -> None:
    assert resolve_logical_type(physical_type) == expected


def test_preview_value_redacts_unseparated_apikey_field() -> None:
    assert preview_value("secret-token", field_name="apikey") == "<redacted>"
    assert preview_value("secret-token", field_name="api_key") == "<redacted>"
    assert preview_value("visible", field_name="molecule_id") == "'visible'"
