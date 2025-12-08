"""Numeric field normalizers."""

from __future__ import annotations

from typing import Any

from bioetl.domain.transform.normalizers.base import is_missing

_MIN_CLINICAL_PHASE = 0
_MAX_CLINICAL_PHASE = 4


def normalize_clinical_phase(value: Any) -> int | None:
    """
    Normalize clinical trial phase values to the inclusive range [0, 4].

    Accepts ints, floats, and numeric strings. Values outside the valid range
    (e.g. sentinel -1 in ChEMBL exports) are treated as missing to keep output
    aligned with Pandera constraints.
    """
    numeric_value = _coerce_phase_value(value)
    if numeric_value is None:
        return None

    if numeric_value < _MIN_CLINICAL_PHASE or numeric_value > _MAX_CLINICAL_PHASE:
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
            raise ValueError(
                "Фаза клинических испытаний должна быть целым числом без дробной части"
            )
        return int(value)

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = float(text)
        except ValueError as exc:
            raise ValueError(
                f"Некорректное числовое значение фазы клинических испытаний: '{value}'"
            ) from exc
        return _coerce_phase_value(parsed)

    raise ValueError(
        f"Ожидалось числовое значение фазы клинических испытаний, получено {type(value).__name__}"
    )


__all__ = ["normalize_clinical_phase"]

