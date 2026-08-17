"""Safe type coercion transformations (no I/O, deterministic, side-effect free).

Implements RULES.md — Safe type conversion utilities for domain transformations.
"""

from __future__ import annotations

import math

_SAFE_CONVERT_SKIP: tuple[type, ...] = (type(None), bool)


def _coerce_to_float(value: object) -> float:
    """Coerce non-None/non-bool value to float; raises on failure."""
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).strip())


def _coerce_to_int(value: object) -> int | None:
    """Coerce non-None/non-bool value to int; returns None for non-finite floats."""
    if isinstance(value, float):
        return int(value) if math.isfinite(value) else None
    if isinstance(value, int):
        return value
    return int(str(value).strip())


def safe_float(
    value: object,
    default: float | None = None,
) -> float | None:
    """Safely convert *value* to float, returning *default* on failure.

    Args:
        value: Input value to convert; None and bool inputs return default immediately.
        default: Value returned when conversion fails or result is non-finite;
            defaults to None.

    Returns:
        Converted float value, or default if conversion fails or value is non-finite.
    """
    if isinstance(value, _SAFE_CONVERT_SKIP):
        return default
    try:
        converted = _coerce_to_float(value)
        return converted if math.isfinite(converted) else default
    except (ValueError, TypeError, OverflowError):
        return default


def safe_int(
    value: object,
    default: int | None = None,
) -> int | None:
    """Safely convert *value* to int, returning *default* on failure.

    Args:
        value: Input value to convert; None and bool inputs return default immediately.
        default: Value returned when conversion fails or result is non-finite;
            defaults to None.

    Returns:
        Converted integer value, or default if conversion fails or value is non-finite.
    """
    if isinstance(value, _SAFE_CONVERT_SKIP):
        return default
    try:
        result = _coerce_to_int(value)
        return result if result is not None else default
    except (ValueError, TypeError):
        return default


def safe_str(
    value: object,
    default: str | None = None,
) -> str | None:
    """Safely convert value to string.

    Useful for fields that may come as int/float from API but need to be
    stored as strings in the schema.

    Args:
        value: Input value to convert
        default: Default value if conversion fails (default: None)

    Returns:
        Converted string or default value
    """
    if value is None:
        return default
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    try:
        return str(value)
    except (ValueError, TypeError):
        return default
