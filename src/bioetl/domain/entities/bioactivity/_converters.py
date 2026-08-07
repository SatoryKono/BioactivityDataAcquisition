"""Primitive type conversion helpers for bioactivity entity."""

from __future__ import annotations

from typing import Any  # Any: needed for _require_field return and _safe_json input

from bioetl.domain.types import JsonDict


def _safe_int(val: object) -> int | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return None


def _safe_float(val: object) -> float | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return None


def _safe_str(val: object) -> str | None:
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    if isinstance(val, int):
        return str(val)
    text = str(val).strip()
    return text or None


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

    if val is None or val == "":
        return None
    if isinstance(val, dict):
        return serialize_to_json(val)
    if isinstance(val, list | tuple):
        return serialize_to_json(val)
    return serialize_to_json({"value": val})
