"""Context correlation utilities for logging and field normalization."""

from __future__ import annotations


def _normalize_correlation_value(value: object | None) -> str | None:
    """Normalize one optional correlation field to a non-empty string."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None
