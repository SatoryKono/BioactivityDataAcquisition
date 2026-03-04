"""Shared validation helpers for composite config models."""

from __future__ import annotations

__all__ = [
    "_require_non_empty",
    "_validate_optional_threshold",
    "_validate_positive",
    "_validate_positive_limit",
    "_validate_threshold_order",
]


def _require_non_empty(value: object, field_name: str) -> None:
    """Validate that a value is not empty."""
    if not value:
        raise ValueError(f"{field_name} cannot be empty")


def _validate_positive(value: int | float, field_name: str) -> None:
    """Validate that a value is positive."""
    if value <= 0:
        raise ValueError(f"{field_name} must be positive, got {value}")


def _validate_positive_limit(limit: int | None, context: str) -> None:
    """Validate that an optional limit is positive if provided."""
    if limit is not None and limit <= 0:
        raise ValueError(f"{context} limit must be positive, got {limit}")


def _validate_optional_threshold(value: float | None, name: str) -> None:
    """Validate that an optional threshold is in [0.0, 1.0] range."""
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0, got {value}")


def _validate_threshold_order(soft: float | None, hard: float | None) -> None:
    """Validate that soft threshold is less than hard threshold."""
    if soft is not None and hard is not None and soft >= hard:
        raise ValueError("soft_fail_threshold must be less than hard_fail_threshold")
