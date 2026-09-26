"""Shared validation helpers for composite config models."""

from __future__ import annotations

__all__ = [
    "coerce_to_tuple",
    "coerce_to_typed_tuple",
    "require_non_empty",
    "validate_optional_threshold",
    "validate_positive",
    "validate_positive_limit",
    "validate_threshold_order",
]


def require_non_empty(value: object, field_name: str) -> None:
    """Validate that a value is not empty.

    Args:
        value: Value to check for emptiness.
        field_name: Human-readable field name used in the error message.

    Raises:
        ValueError: If the value is falsy (None, empty string, empty collection).
    """
    if not value:
        raise ValueError(f"{field_name} cannot be empty")


def coerce_to_tuple(obj: object, attr: str) -> None:
    """Convert list values on a dataclass attribute to tuples."""
    val = getattr(obj, attr, None)
    if val is None or not isinstance(val, list):
        return
    object.__setattr__(obj, attr, tuple(val))


def coerce_to_typed_tuple(obj: object, attr: str, factory: type) -> None:
    """Convert list values to tuples, coercing dict items into the factory type."""
    val = getattr(obj, attr, None)
    if val is None or not isinstance(val, list):
        return
    converted = tuple(
        factory(**item) if isinstance(item, dict) else item for item in val
    )
    object.__setattr__(obj, attr, converted)


def validate_positive(value: int | float, field_name: str) -> None:
    """Validate that a value is positive.

    Args:
        value: Numeric value to validate.
        field_name: Human-readable field name used in the error message.

    Raises:
        ValueError: If the value is zero or negative.
    """
    if value <= 0:
        raise ValueError(f"{field_name} must be positive, got {value}")


def validate_positive_limit(limit: int | None, context: str) -> None:
    """Validate that an optional limit is positive if provided.

    Args:
        limit: Optional integer limit to validate.
        context: Human-readable context label used in the error message.

    Raises:
        ValueError: If limit is not None and is not positive.
    """
    if limit is not None and limit <= 0:
        raise ValueError(f"{context} limit must be positive, got {limit}")


def validate_optional_threshold(value: float | None, name: str) -> None:
    """Validate that an optional threshold is in [0.0, 1.0] range.

    Args:
        value: Optional float threshold to validate.
        name: Human-readable threshold name used in the error message.

    Raises:
        ValueError: If value is not None and falls outside [0.0, 1.0].
    """
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0, got {value}")


def validate_threshold_order(soft: float | None, hard: float | None) -> None:
    """Validate that soft threshold is less than hard threshold.

    Args:
        soft: Optional soft-fail threshold value.
        hard: Optional hard-fail threshold value.

    Raises:
        ValueError: If both values are provided and soft >= hard.
    """
    if soft is not None and hard is not None and soft >= hard:
        raise ValueError("soft_fail_threshold must be less than hard_fail_threshold")


# Private aliases retained for residual call sites during rename migration.
_require_non_empty = require_non_empty
_coerce_to_tuple = coerce_to_tuple
_coerce_to_typed_tuple = coerce_to_typed_tuple
_validate_positive = validate_positive
_validate_positive_limit = validate_positive_limit
_validate_optional_threshold = validate_optional_threshold
_validate_threshold_order = validate_threshold_order
