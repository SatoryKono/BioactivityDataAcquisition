"""Shared numeric coercion helpers for normalization profiles."""

from __future__ import annotations

from bioetl.domain.normalization.text import normalize_string


def coerce_profile_quasi_enum_numeric(value: object) -> float | None:
    """Normalize numeric-like provider codes into a comparable float."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        return _coerce_profile_quasi_enum_numeric_text(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _coerce_profile_quasi_enum_numeric_text(value: str) -> float | None:
    cleaned = normalize_string(value)
    if cleaned is None:
        return None
    return _float_or_none(cleaned)


def _float_or_none(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None
