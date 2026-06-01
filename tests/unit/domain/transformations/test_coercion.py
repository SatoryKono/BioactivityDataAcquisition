"""Tests for safe type coercion transformations.

Tests for safe_float, safe_int, safe_str.
"""

from __future__ import annotations

import pytest

from bioetl.domain.transformations.coercion import safe_float, safe_int, safe_str


@pytest.mark.unit
class TestSafeFloat:
    """Tests for safe_float function."""

    def test_int_input(self) -> None:
        assert safe_float(42) == pytest.approx(42.0)

    def test_float_input(self) -> None:
        assert safe_float(3.14) == pytest.approx(3.14)

    def test_string_input(self) -> None:
        assert safe_float("3.14") == pytest.approx(3.14)

    def test_string_with_whitespace(self) -> None:
        assert safe_float("  3.14  ") == pytest.approx(3.14)

    def test_none_returns_default(self) -> None:
        assert safe_float(None) is None

    def test_none_with_custom_default(self) -> None:
        assert safe_float(None, default=0.0) == pytest.approx(0.0)

    def test_bool_returns_default(self) -> None:
        assert safe_float(True) is None
        assert safe_float(False) is None

    def test_invalid_string_returns_default(self) -> None:
        assert safe_float("not_a_number") is None

    def test_nan_returns_default(self) -> None:
        assert safe_float(float("nan")) is None

    def test_inf_returns_default(self) -> None:
        assert safe_float(float("inf")) is None
        assert safe_float(float("-inf")) is None

    def test_custom_default_on_failure(self) -> None:
        assert safe_float("bad", default=-1.0) == pytest.approx(-1.0)


@pytest.mark.unit
class TestSafeInt:
    """Tests for safe_int function."""

    def test_coercion_safe_int__int_input__c9dca975(self) -> None:
        assert safe_int(42) == 42

    def test_coercion_safe_int__float_input__def9b800(self) -> None:
        assert safe_int(42.9) == 42

    def test_coercion_safe_int__string_input__bf388a02(self) -> None:
        assert safe_int("42") == 42

    def test_coercion_safe_int__with_whitespace__cda419d7(self) -> None:
        assert safe_int("  42  ") == 42

    def test_coercion_safe_int__none_returns_default__4d5aa279(self) -> None:
        assert safe_int(None) is None

    def test_bool_returns_default__test_safe_int_domain_transformations_test_coercion_72(
        self,
    ) -> None:
        assert safe_int(True) is None
        assert safe_int(False) is None

    def test_coercion_safe_int__returns_default__26270d42(self) -> None:
        assert safe_int("not_a_number") is None

    def test_nan_float_returns_default(self) -> None:
        assert safe_int(float("nan")) is None

    def test_inf_float_returns_default(self) -> None:
        assert safe_int(float("inf")) is None

    def test_custom_default(self) -> None:
        assert safe_int("bad", default=-1) == -1


@pytest.mark.unit
class TestSafeStr:
    """Tests for safe_str function."""

    def test_coercion_safe_str__string_input__e24f54b6(self) -> None:
        assert safe_str("hello") == "hello"

    def test_coercion_safe_str__int_input__42ef2135(self) -> None:
        assert safe_str(42) == "42"

    def test_float_integer_input(self) -> None:
        # Float with integer value should drop decimal
        assert safe_str(42.0) == "42"

    def test_float_non_integer_input(self) -> None:
        assert safe_str(3.14) == "3.14"

    def test_coercion_safe_str__none_returns_default__573e725b(self) -> None:
        assert safe_str(None) is None

    def test_coercion_safe_str__with_custom_default__ffbf48e2(self) -> None:
        assert safe_str(None, default="N/A") == "N/A"
