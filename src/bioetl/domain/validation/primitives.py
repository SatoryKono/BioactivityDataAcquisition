"""Primitive value validation functions (no I/O).

Implements validation rules for basic primitive types:
- Non-empty strings
- Non-negative numeric values
- Positive integers

Requirements:
- REQ-ARCH-003: No I/O in domain layer
- REFACTOR-004: Domain logic separation from use-case layer

See also:
- docs/RULES.md §1.1 (Domain — pure functions)
"""

from __future__ import annotations

from bioetl.domain.transformations import safe_int

__all__ = [
    "validate_non_empty_string",
    "validate_non_negative",
    "validate_positive_int",
]

# =============================================================================
# Numeric Validation
# =============================================================================


def validate_positive_int(value: object) -> int | None:
    """Validate integer is positive (>= 1) or return None.

    Used for validating IDs, counts, and other positive integer fields.

    Args:
        value: Raw value to validate (string, int, or other convertible type).

    Returns:
        Valid int (>= 1) or None if invalid/non-positive.

    Example:
        >>> validate_positive_int(42)
        42
        >>> validate_positive_int("123")
        123
        >>> validate_positive_int(0)
        None
        >>> validate_positive_int(-1)
        None
        >>> validate_positive_int("invalid")
        None

    """
    int_value = safe_int(value)
    if int_value is not None and int_value < 1:
        return None
    return int_value


def validate_non_negative(value: object) -> float | None:
    """Validate numeric value is non-negative (>= 0) or return None.

    Used for validating concentrations, counts, and other non-negative fields.

    Args:
        value: Raw value to validate.

    Returns:
        Valid float (>= 0) or None if invalid/negative.

    Example:
        >>> validate_non_negative(0.0)
        0.0
        >>> validate_non_negative(42.5)
        42.5
        >>> validate_non_negative(-1.0)
        None
        >>> validate_non_negative("invalid")
        None

    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        float_value = float(str(value).strip())
        if float_value < 0:
            return None
        return float_value
    except (ValueError, TypeError):
        return None


# =============================================================================
# String Validation
# =============================================================================


def validate_non_empty_string(value: str | None) -> str | None:
    """Validate string is non-empty after stripping whitespace.

    Args:
        value: String to validate.

    Returns:
        Stripped string if non-empty, None otherwise.

    Example:
        >>> validate_non_empty_string("  hello  ")
        'hello'
        >>> validate_non_empty_string("   ")
        None
        >>> validate_non_empty_string(None)
        None

    """
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped if stripped else None
