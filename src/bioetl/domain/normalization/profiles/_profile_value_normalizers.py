"""Shared value-level normalizers for profile normalization."""

from __future__ import annotations

import math
from collections.abc import Callable

from bioetl.domain.normalization.json import (
    deserialize_json_value,
    serialize_json_canonical,
)
from bioetl.domain.normalization.open_access import normalize_governed_oa_status
from bioetl.domain.normalization.rules import (
    normalize_binary_flag,
    normalize_boolean,
    normalize_case,
    normalize_cross_pipeline_case,
)
from bioetl.domain.normalization.text import normalize_string

_UNHANDLED = object()


def _preserve_unknown_lexeme(normalized: str) -> str | None:
    """Keep unknown governed vocabulary tokens as-is."""
    return normalized


def _preserve_unknown_uppercase_lexeme(normalized: str) -> str | None:
    """Keep unknown governed vocabulary tokens in cross-pipeline uppercase form."""
    return normalize_cross_pipeline_case(normalized, "uppercase")


def _normalize_governed_vocabulary_value(
    value: object,
    *,
    allowed_values: frozenset[str],
    fallback: Callable[[str], str | None] | None = None,
) -> object:
    if not isinstance(value, str):
        return value
    normalized = normalize_string(value)
    if normalized is None:
        return None
    canonical = normalize_case(normalized, allowed_values)
    if canonical is not None:
        return canonical
    return fallback(normalized) if fallback is not None else None


def normalize_profile_governed_vocabulary(
    value: object,
    *,
    allowed_values: frozenset[str],
    preserve_unknown: bool = False,
) -> object:
    """Normalize one governed text vocabulary against a canonical registry."""
    return _normalize_governed_vocabulary_value(
        value,
        allowed_values=allowed_values,
        fallback=_preserve_unknown_lexeme if preserve_unknown else None,
    )


def normalize_profile_governed_uppercase_vocabulary(
    value: object,
    *,
    allowed_values: frozenset[str],
    preserve_unknown: bool = False,
) -> object:
    """Normalize one governed vocabulary and uppercase unknown lexemes when kept."""
    return _normalize_governed_vocabulary_value(
        value,
        allowed_values=allowed_values,
        fallback=_preserve_unknown_uppercase_lexeme if preserve_unknown else None,
    )


def normalize_profile_json_string_list_vocabulary_strict(
    value: object,
    *,
    allowed_values: frozenset[str],
) -> object:
    """Normalize one JSON-array string element-wise against a governed registry."""
    parsed = _parse_json_string_list(value)
    if parsed is None:
        return None
    normalized_values = [
        _normalize_json_string_list_vocabulary_item(
            item,
            allowed_values=allowed_values,
        )
        for item in parsed
    ]
    if any(item is None for item in normalized_values):
        return None
    return serialize_json_canonical(normalized_values)


def _parse_json_string_list(value: object) -> list[object] | None:
    if not isinstance(value, str):
        return None
    normalized = normalize_string(value)
    if normalized is None:
        return None
    try:
        parsed = deserialize_json_value(normalized)
    except ValueError:
        return None
    return parsed if isinstance(parsed, list) else None


def _normalize_json_string_list_vocabulary_item(
    item: object,
    *,
    allowed_values: frozenset[str],
) -> str | None:
    canonical = normalize_profile_governed_vocabulary(
        item,
        allowed_values=allowed_values,
        preserve_unknown=False,
    )
    return canonical if isinstance(canonical, str) else None


def normalize_profile_boolean(value: object) -> bool | None:
    """Normalize common boolean-like profile fields to canonical bool."""
    return normalize_boolean(value)


def normalize_profile_oa_status(value: object) -> str | None:
    """Normalize OA status against the shared publication OA-status registry."""
    return normalize_governed_oa_status(value)


def normalize_profile_binary_flag(value: object) -> int | None:
    """Normalize common boolean-like profile fields to canonical 0/1."""
    return normalize_binary_flag(value)


def normalize_profile_int(value: object) -> object:
    """Coerce one integer-like value to stable scalar semantics."""
    if type(value) in {type(None), bool, int}:
        return value
    coerced = _coerce_profile_int(value)
    if coerced is _UNHANDLED:
        return value
    return coerced


def normalize_profile_float(value: object) -> object:
    """Coerce one float-like value to stable finite scalar semantics."""
    if type(value) in {type(None), bool}:
        return value
    return _normalize_profile_float_value(value)


def _normalize_profile_float_value(value: object) -> object:
    coerced = _coerce_profile_float(value)
    if coerced is _UNHANDLED:
        return value
    return _finalize_profile_float(coerced, fallback=value)


def _coerce_profile_int(value: object) -> int | str | float | None | object:
    if isinstance(value, float):
        return int(value) if value.is_integer() else value
    if not isinstance(value, str):
        return _UNHANDLED
    return _coerce_profile_int_text(value)


def _coerce_profile_int_text(value: str) -> int | str | None:
    normalized = normalize_string(value)
    if normalized is None:
        return None
    return _parse_profile_int_text(normalized)


def _parse_profile_int_text(value: str) -> int | str:
    try:
        return int(value)
    except ValueError:
        return value


def _coerce_profile_float(value: object) -> float | str | None | object:
    if isinstance(value, int | float):
        return float(value)
    if not isinstance(value, str):
        return _UNHANDLED
    normalized = normalize_string(value)
    if normalized is None:
        return None
    try:
        return float(normalized)
    except ValueError:
        return normalized


def _finalize_profile_float(
    coerced: float | str | None | object,
    *,
    fallback: object,
) -> object:
    if coerced is None or isinstance(coerced, str):
        return coerced
    if isinstance(coerced, float):
        return round(coerced, 10) if math.isfinite(coerced) else None
    return fallback
