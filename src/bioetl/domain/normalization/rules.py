"""Normalization rules for case handling and unit canonicalization."""

from __future__ import annotations

from typing import Any

from bioetl.domain.normalization.text import normalize_string

__all__ = [
    "BINARY_FLAG_MAPPING",
    "NULL_PATTERNS",
    "OPERATOR_MAPPING",
    "UNIT_MAPPING",
    "normalize_binary_flag",
    "normalize_boolean",
    "normalize_case",
    "normalize_cross_pipeline_case",
    "normalize_null",
    "normalize_operator",
    "normalize_unit",
]

NULL_PATTERNS: frozenset[str] = frozenset(
    [
        "",
        " ",
        ".",
        "..",
        "...",
        "-",
        "--",
        "<NA>",
        "<NULL>",
        "MISSING",
        "N/A",
        "NA",
        "NAN",
        "NONE",
        "NOT_APPLICABLE",
        "NOT_AVAILABLE",
        "NULL",
        "NULL_VALUE",
        "None",
        "UNKNOWN",
        "missing",
        "n/a",
        "na",
        "nan",
        "none",
        "not_applicable",
        "not_available",
        "null",
        "unknown",
    ]
)
UNIT_MAPPING: dict[str, str] = {
    "nL": "nL",
    "NL": "nL",
    "nl": "nL",
    "uL": "µL",
    "UL": "µL",
    "µL": "µL",
    "mL": "mL",
    "ML": "mL",
    "ml": "mL",
    "L": "L",
    "l": "L",
    "nM": "nM",
    "NM": "nM",
    "nm": "nM",
    "uM": "µM",
    "UM": "µM",
    "µM": "µM",
    "μM": "µM",
    "mM": "mM",
    "MM": "mM",
    "mm": "mM",
    "M": "M",
    "m": "M",
    "pM": "pM",
    "PM": "pM",
    "pm": "pM",
    "g": "g",
    "G": "g",
    "mg": "mg",
    "MG": "mg",
    "ug": "µg",
    "UG": "µg",
    "µg": "µg",
    "μg": "µg",
    "ng": "ng",
    "NG": "ng",
    "pg": "pg",
    "PG": "pg",
    "%": "%",
    "percent": "%",
    "PERCENT": "%",
    "U": "U",
    "u": "U",
    "units": "U",
    "UNITS": "U",
}

BINARY_FLAG_MAPPING: dict[str, bool] = {
    "1": True,
    "y": True,
    "yes": True,
    "true": True,
    "t": True,
    "0": False,
    "n": False,
    "no": False,
    "false": False,
    "f": False,
}

OPERATOR_MAPPING: dict[str, str] = {
    "=": "=",
    "==": "=",
    "eq": "=",
    "<": "<",
    "lt": "<",
    "≤": "<=",
    "<=": "<=",
    "lte": "<=",
    ">": ">",
    "gt": ">",
    "≥": ">=",
    ">=": ">=",
    "gte": ">=",
    "~": "~",
    "≈": "~",
    "approx": "~",
}


def _find_case_match(normalized: str, allowed_values: frozenset[str]) -> str | None:
    """Find case-insensitive match in allowed values."""
    for allowed_value in allowed_values:
        if normalized.upper() == allowed_value.upper():
            # Return the allowed value's original case to preserve enum casing
            return allowed_value
    return None


def normalize_case(
    value: Any,  # Any: Generic input value from various sources
    allowed_values: frozenset[str] | None = None,
) -> str | None:
    """Normalize case for enum-like fields."""
    if value is None or not isinstance(value, str):
        return None
    normalized = normalize_string(value)
    if normalized is None:
        return None
    if allowed_values is not None:
        return _find_case_match(normalized, allowed_values)
    return normalized


def normalize_unit(
    value: Any,  # Any: Generic input value from various sources
) -> str | None:
    """Canonicalize unit strings to standard format."""
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    normalized = normalize_string(value)
    if normalized is None:
        return None
    return UNIT_MAPPING.get(normalized, normalized)


def _normalize_int_boolean(value: int) -> bool | None:
    if value in {0, 1}:
        return bool(value)
    return None


def _normalize_float_boolean(value: float) -> bool | None:
    if value in {0.0, 1.0}:
        return bool(int(value))
    return None


def _normalize_str_boolean(value: str) -> bool | None:
    normalized = normalize_string(value)
    if normalized is None:
        return None
    return BINARY_FLAG_MAPPING.get(normalized.lower())


_BOOLEAN_NORMALIZERS = {
    bool: lambda value: value,
    int: _normalize_int_boolean,
    float: _normalize_float_boolean,
    str: _normalize_str_boolean,
}


def normalize_boolean(
    value: Any,  # Any: Accepts various input types for boolean conversion
) -> bool | None:
    """Coerce common source-system boolean encodings to canonical bool."""
    if value is None:
        return None
    normalizer = _BOOLEAN_NORMALIZERS.get(type(value))
    return normalizer(value) if normalizer is not None else None


def normalize_binary_flag(
    value: Any,  # Any: Handles various input representations for binary flags
) -> int | None:
    """Coerce common boolean-like values to the canonical 0/1 flag contract."""
    normalized = normalize_boolean(value)
    if normalized is None:
        return None
    return int(normalized)


def normalize_operator(
    value: Any,  # Any: Accepts various input types for operator normalization
    allowed_values: frozenset[str] | None = None,
) -> str | None:
    """Canonicalize comparison operators, including Unicode variants."""
    if value is None:
        return None
    normalized = normalize_string(str(value))
    if normalized is None:
        return None
    operator = OPERATOR_MAPPING.get(normalized.lower(), normalized)
    if allowed_values is not None and operator not in allowed_values:
        return None
    return operator


def normalize_null(
    value: Any,  # Any: Generic input value from various sources
) -> Any:  # Any: Generic return type to preserve original value type
    """Convert pseudo-null values to proper None values."""
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    normalized = normalize_string(value)
    if normalized is None:
        return None
    if normalized in NULL_PATTERNS:
        return None
    return value


def normalize_enum_case(
    value: Any,  # Any: Generic input value from various sources
    allowed_values: frozenset[str],
) -> str | None:
    """Normalize enum value with case normalization and validation."""
    return normalize_case(value, allowed_values)


def _apply_case_strategy(normalized: str, strategy: str) -> str:
    """Apply the specified case strategy to normalized string."""
    strategy_map = {
        "uppercase": normalized.upper(),
        "lowercase": normalized.lower(),
        "preserve": normalized,
    }
    return strategy_map.get(strategy, normalized)


def normalize_cross_pipeline_case(
    value: str, strategy: str = "uppercase"
) -> str | None:
    """Normalize case using one consistent strategy across pipelines."""
    if value is None or not isinstance(value, str):
        return None
    normalized = normalize_string(value)
    if normalized is None:
        return None
    return _apply_case_strategy(normalized, strategy)
