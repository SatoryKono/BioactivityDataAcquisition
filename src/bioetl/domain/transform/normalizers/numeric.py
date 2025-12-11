"""Numeric field normalizers."""

from __future__ import annotations

from typing import Any

from bioetl.domain.transform.normalizers.base import is_missing

MIN_CLINICAL_PHASE = 0
MAX_CLINICAL_PHASE = 4


def normalize_clinical_phase(value: Any) -> int | None:
    """
    Normalize clinical trial phase values to the inclusive range [0, 4].

    Accepts ints, floats, and numeric strings. Values outside the valid range
    or non-integer floats (e.g. 1.5) are treated as missing to keep output
    aligned with Pandera constraints and avoid pipeline failures on dirty data.
    """
    numeric_value = _coerce_phase_value(value)
    if numeric_value is None:
        return None

    if numeric_value < MIN_CLINICAL_PHASE or numeric_value > MAX_CLINICAL_PHASE:
        return None

    return numeric_value


def _coerce_phase_value(value: Any) -> int | None:
    """Coerce incoming value to an integer phase or None."""
    if is_missing(value):
        return None

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if is_missing(value):
            return None
        if not value.is_integer():
            return None
        return int(value)

    if isinstance(value, str):
        text = value.strip()
        if not text or text == "<NA>":
            return None
        try:
            parsed = float(text)
        except ValueError as exc:
            raise ValueError(
                f"Invalid numeric value for clinical trial phase: '{value}'"
            ) from exc
        return _coerce_phase_value(parsed)

    # Handle pandas NAType explicitly
    # Use is_missing which handles pd.NA without importing pandas

    raise ValueError(
        "Expected numeric value for clinical trial phase, "
        f"got {type(value).__name__}"
    )


__all__ = ["normalize_clinical_phase"]
