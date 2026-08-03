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
"""Tests for primitive value validation functions.

Tests for validate_positive_int, validate_non_negative, validate_non_empty_string.
"""

from __future__ import annotations

import pytest

from bioetl.domain.validation.primitives import (
    validate_non_empty_string,
    validate_non_negative,
    validate_positive_int,
)


@pytest.mark.unit
class TestValidatePositiveInt:
    """Tests for validate_positive_int function."""

    def test_validate_positive_int__valid_positive_int__00eeb372(self) -> None:
        assert validate_positive_int(42) == 42

    def test_valid_string_int(self) -> None:
        assert validate_positive_int("123") == 123

    def test_one_is_valid(self) -> None:
        assert validate_positive_int(1) == 1

    def test_zero_returns_none(self) -> None:
        assert validate_positive_int(0) is None

    def test_validate_positive_int__returns_none__f02e3610(self) -> None:
        assert validate_positive_int(-1) is None

    def test_validate_positive_int__string_returns_none__57edfe86(self) -> None:
        assert validate_positive_int("invalid") is None

    def test_validate_positive_int__none_returns_none__fb978417(self) -> None:
        assert validate_positive_int(None) is None

    def test_validate_positive_int__bool_returns_none__2c677924(self) -> None:
        # bool is skipped by safe_int
        assert validate_positive_int(True) is None

    def test_float_value(self) -> None:
        result = validate_positive_int(42.9)
        assert result == 42


@pytest.mark.unit
class TestValidateNonNegative:
    """Tests for validate_non_negative function."""

    def test_zero_is_valid(self) -> None:
        assert validate_non_negative(0.0) == pytest.approx(0.0)

    def test_positive_float(self) -> None:
        assert validate_non_negative(42.5) == pytest.approx(42.5)

    def test_positive_int(self) -> None:
        result = validate_non_negative(10)
        assert result == pytest.approx(10.0)

    def test_validate_non_negative__returns_none__1a3435af(self) -> None:
        assert validate_non_negative(-1.0) is None

    def test_validate_non_negative__none_returns_none__df8e24f5(self) -> None:
        assert validate_non_negative(None) is None

    def test_validate_non_negative__bool_returns_none__f2e70b00(self) -> None:
        assert validate_non_negative(True) is None
        assert validate_non_negative(False) is None

    def test_validate_non_negative__string_returns_none__acd96308(self) -> None:
        assert validate_non_negative("invalid") is None

    def test_valid_string_number(self) -> None:
        assert validate_non_negative("42.5") == pytest.approx(42.5)

    def test_validate_non_negative__whitespace_string__cd88ccea(self) -> None:
        assert validate_non_negative("  42  ") == pytest.approx(42.0)


@pytest.mark.unit
class TestValidateNonEmptyString:
    """Tests for validate_non_empty_string function."""

    def test_non_empty_string__valid_string__d49b0991(self) -> None:
        assert validate_non_empty_string("hello") == "hello"

    def test_non_empty_string__strips_whitespace__1ce777d7(self) -> None:
        assert validate_non_empty_string("  hello  ") == "hello"

    def test_non_empty_string__only_returns_none__a87a92a9(self) -> None:
        assert validate_non_empty_string("   ") is None

    def test_non_empty_string__string_returns_none__0cc1be95(self) -> None:
        assert validate_non_empty_string("") is None

    def test_non_empty_string__none_returns_none__f5ca88d1(self) -> None:
        assert validate_non_empty_string(None) is None
