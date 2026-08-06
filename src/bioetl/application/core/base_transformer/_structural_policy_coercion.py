"""Type coercion helpers for schema-aware structural policy."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from math import isfinite

from ._structural_policy_types import StructuralFieldSpec

_BOOL_TRUE_VALUES = frozenset({"1", "true", "yes", "y"})
_BOOL_FALSE_VALUES = frozenset({"0", "false", "no", "n"})


def coerce_value(value: object, contract: StructuralFieldSpec) -> object | None:
    """Return coerced value when conversion is valid, otherwise None."""
    allow_string_coercion = contract.coercion_policy != "no_string_coercion"
    if contract.logical_type == "integer":
        return _coerce_integer(value, allow_string_coercion=allow_string_coercion)
    if contract.logical_type == "float":
        return _coerce_float(value, allow_string_coercion=allow_string_coercion)
    if contract.logical_type == "boolean":
        return _coerce_boolean(
            value,
            allow_string_coercion=allow_string_coercion,
            true_values=contract.boolean_true_values,
            false_values=contract.boolean_false_values,
        )
    return value


def _coerce_integer(
    value: object,
    *,
    allow_string_coercion: bool,
) -> int | None:
    """Coerce value to integer when semantically valid."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return _coerce_integer_from_float(value)
    if isinstance(value, str):
        return _coerce_integer_from_string(
            value,
            allow_string_coercion=allow_string_coercion,
        )
    return None


def _coerce_integer_from_float(value: float) -> int | None:
    """Coerce integer-compatible float values."""
    if not isfinite(value) or not value.is_integer():
        return None
    return int(value)


def _coerce_integer_from_string(
    value: str,
    *,
    allow_string_coercion: bool,
) -> int | None:
    """Coerce integer-compatible strings."""
    if not allow_string_coercion:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        decimal_value = Decimal(normalized)
        # Reject NaN/Infinity before integrality checks (Decimal('NaN') compares
        # as unequal to itself and must not become int).
        if not decimal_value.is_finite():
            return None
        if decimal_value != decimal_value.to_integral_value():
            return None
        return int(decimal_value)
    except (InvalidOperation, ValueError, OverflowError):
        return None


def _coerce_float(
    value: object,
    *,
    allow_string_coercion: bool,
) -> float | None:
    """Coerce value to float when semantically valid."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        return value if isfinite(value) else None
    if isinstance(value, str):
        if not allow_string_coercion:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        try:
            float_value = float(normalized)
        except ValueError:
            return None
        return float_value if isfinite(float_value) else None
    return None


def _coerce_boolean(
    value: object,
    *,
    allow_string_coercion: bool,
    true_values: tuple[str, ...],
    false_values: tuple[str, ...],
) -> bool | None:
    """Coerce value to boolean when semantically valid."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value in (0, 1):
            return bool(value)
        return None
    if isinstance(value, str):
        if not allow_string_coercion:
            return None
        normalized = value.strip().lower()
        true_vocabulary = frozenset(true_values) if true_values else _BOOL_TRUE_VALUES
        false_vocabulary = (
            frozenset(false_values) if false_values else _BOOL_FALSE_VALUES
        )
        if normalized in true_vocabulary:
            return True
        if normalized in false_vocabulary:
            return False
    return None
