"""Primitive type conversion helpers for bioactivity entity."""

from __future__ import annotations

import math
from typing import Any  # Any: needed for _require_field return and _safe_json input

from bioetl.domain.types import JsonDict


def _finite_number(val: object) -> float | None:
    """Return a finite number, rejecting bool and non-numeric values."""
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return None
    number = float(val)
    if not math.isfinite(number):
        return None
    return number


def _is_unsupported_numeric_input(val: object) -> bool:
    """Return whether *val* must not be coerced to a numeric value."""
    return val is None or isinstance(val, bool)


def _safe_int(val: object) -> int | None:
    if _is_unsupported_numeric_input(val):
        return None
    number = _finite_number(val)
    if number is not None:
        if number.is_integer():
            return int(number)
        return None
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return None


def _safe_float(val: object) -> float | None:
    if _is_unsupported_numeric_input(val):
        return None
    number = _finite_number(val)
    if number is not None:
        return number
    try:
        parsed = float(str(val).strip())
    except (ValueError, TypeError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _safe_str_from_float(val: float) -> str | None:
    if not math.isfinite(val):
        return None
    if val.is_integer():
        return str(int(val))
    return str(val)


def _safe_str_from_text(val: object) -> str | None:
    text = str(val).strip()
    if text:
        return text
    return None


def _safe_str(val: object) -> str | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, float):
        return _safe_str_from_float(val)
    if isinstance(val, int):
        return str(val)
    return _safe_str_from_text(val)


def _require_field(
    raw_data: JsonDict,
    field: str,
) -> Any:  # Any: JsonDict values are heterogeneous (str|int|float|None)
    value = raw_data.get(field)
    if value is None:
        raise ValueError(f"raw_data must contain '{field}'")
    return value


def _safe_json(val: object) -> str | None:
    """Convert to JSON string if not None/empty."""
    from bioetl.domain.serialization import serialize_to_json

    if val is None:
        return None
    if val == "":
        return None
    if isinstance(val, dict):
        return serialize_to_json(val)
    if isinstance(val, list | tuple):
        return serialize_to_json(val)
    return serialize_to_json({"value": val})
