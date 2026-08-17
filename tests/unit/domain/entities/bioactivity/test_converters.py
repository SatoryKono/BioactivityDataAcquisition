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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Targeted unit tests for bioactivity converters (partial coverage tail / #6896)."""

from __future__ import annotations

import math

import pytest

from bioetl.domain.entities.bioactivity._converters import (
    _require_field,
    _safe_float,
    _safe_int,
    _safe_json,
    _safe_str,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (True, None),
        (False, None),
        (12, 12),
        (5.0, 5),
        (" 42 ", 42),
        ("nope", None),
        ("3", 3),
        (3.5, None),
        (math.nan, None),
        (math.inf, None),
    ],
)
def test_safe_int_edges(value: object, expected: int | None) -> None:
    assert _safe_int(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (True, None),
        (" 1.5 ", 1.5),
        ("bad", None),
        (2, 2.0),
        (math.nan, None),
        (math.inf, None),
        (-math.inf, None),
        ("nan", None),
        ("inf", None),
    ],
)
def test_safe_float_edges(value: object, expected: float | None) -> None:
    assert _safe_float(value) == expected


def test_safe_str_and_require_field() -> None:
    assert _safe_str(None) is None
    assert _safe_str(7) == "7"
    assert _safe_str(math.nan) is None
    assert _safe_str(math.inf) is None
    assert _require_field({"a": 1}, "a") == 1
    with pytest.raises(ValueError, match="raw_data must contain"):
        _require_field({}, "missing")


def test_safe_json_serializes_structures() -> None:
    assert _safe_json(None) is None
    assert _safe_json("") is None
    assert _safe_json({"k": "v"}) is not None
    assert _safe_json([1, 2]) is not None
    assert _safe_json("x") is not None
