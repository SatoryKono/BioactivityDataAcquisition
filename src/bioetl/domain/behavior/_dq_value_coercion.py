"""DQ value coercion helper functions.

Extracted from _dq_rule_evaluators.py to meet file size limits.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.config.validation import FieldValidation


def _is_present(value: object) -> bool:
    return value is not None


def _coerce_list_like(value: object) -> list[object] | None:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple | set):
        return list(value)
    if not isinstance(value, str):
        return None
    return _coerce_string_list_like(value)


def _coerce_numeric_value(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _violates_minimum(numeric_value: float, rule: FieldValidation) -> bool:
    return rule.min_value is not None and numeric_value < rule.min_value


def _violates_maximum(numeric_value: float, rule: FieldValidation) -> bool:
    return rule.max_value is not None and numeric_value > rule.max_value


def _coerce_string_list_like(value: str) -> list[object] | None:
    stripped = value.strip()
    if not stripped:
        return []
    if not _looks_like_json_list(stripped):
        return None
    return _decode_json_list_like(stripped)


def _looks_like_json_list(value: str) -> bool:
    return value.startswith("[") and value.endswith("]")


def _decode_json_list_like(value: str) -> list[object] | None:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, list) else None


__all__ = [
    "_coerce_list_like",
    "_coerce_numeric_value",
    "_is_present",
    "_violates_maximum",
    "_violates_minimum",
]
