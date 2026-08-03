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
"""Unit tests for span attribute coercion helpers."""

from __future__ import annotations

import pytest

from bioetl.application.observability.span_attribute_values import (
    _bool_sequence,
    _float_sequence,
    _int_sequence,
    _sequence_items,
    _string_sequence,
    coerce_span_attribute_value,
)

pytestmark = pytest.mark.unit


def test_sequence_items_rejects_scalars_and_accepts_sequences() -> None:
    assert _sequence_items("text") is None
    assert _sequence_items(b"bytes") is None
    assert _sequence_items(["a", "b"]) == ["a", "b"]


def test_sequence_matchers_cover_empty_and_typed_sequences() -> None:
    assert _string_sequence([]) == ()
    assert _string_sequence(["a", "b"]) == ["a", "b"]
    assert _string_sequence(["a", 1]) is None

    assert _bool_sequence([]) == ()
    assert _bool_sequence([True, False]) == [True, False]
    assert _bool_sequence([True, 1]) is None

    assert _int_sequence([]) == ()
    assert _int_sequence([1, 2]) == [1, 2]
    assert _int_sequence([1, True]) is None

    assert _float_sequence([]) == ()
    assert _float_sequence([1.0, 2.0]) == [1.0, 2.0]
    assert _float_sequence([1.0, 2]) is None


def test_coerce_span_attribute_value_handles_scalars_sequences_and_fallback() -> None:
    assert coerce_span_attribute_value(True) is True
    assert coerce_span_attribute_value("text") == "text"
    assert coerce_span_attribute_value(7) == 7
    assert coerce_span_attribute_value(1.5) == 1.5
    assert coerce_span_attribute_value(["a", "b"]) == ["a", "b"]
    assert coerce_span_attribute_value([True, False]) == [True, False]
    assert coerce_span_attribute_value([1, 2]) == [1, 2]
    assert coerce_span_attribute_value([1.0, 2.0]) == [1.0, 2.0]
    assert coerce_span_attribute_value(["a", 1]) == "['a', 1]"
    assert coerce_span_attribute_value({"a": 1}) == "{'a': 1}"
