"""Shared pure validators for domain entity invariants."""

from __future__ import annotations

__all__ = [
    "require_non_empty_str",
    "require_positive_id",
]


def require_positive_id(value: int, field_name: str) -> None:
    """Raise ValueError when ``value`` is not a positive integer."""
    if value < 1:
        raise ValueError(f"{field_name} must be > 0, got {value}")


def require_non_empty_str(value: str, field_name: str) -> None:
    """Raise ValueError when ``value`` is empty or whitespace-only."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
