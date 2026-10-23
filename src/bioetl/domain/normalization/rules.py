"""Normalization rules for case handling and unit canonicalization."""

from __future__ import annotations

from typing import Any

from bioetl.domain.exceptions import ValidationError
from bioetl.domain.normalization._chembl_units import (
    CHEMBL_STANDARD_UNIT_CANONICALS,
)
from bioetl.domain.normalization._chembl_units import (
    normalize_standard_unit as normalize_chembl_standard_unit,
)

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
_NULL_PATTERNS_UPPER: frozenset[str] = frozenset(
    pattern.upper() for pattern in NULL_PATTERNS
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
    norm_upper = normalized.upper()
    for allowed_value in allowed_values:
        if norm_upper == allowed_value.upper():
            # Return the allowed value's original case to preserve enum casing
            return allowed_value
    return None


def normalize_case(
    value: Any,  # Any: Generic input value from various sources
    allowed_values: frozenset[str] | None = None,
) -> str | None:
    """Normalize case for enum-like fields."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if allowed_values is not None:
        return _find_case_match(stripped, allowed_values)
    return stripped


def normalize_unit(
    value: Any,  # Any: Generic input value from various sources
) -> str | None:
    """Canonicalize unit strings to standard format."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    chembl_standard_unit = normalize_chembl_standard_unit(stripped)
    if chembl_standard_unit in CHEMBL_STANDARD_UNIT_CANONICALS:
        return chembl_standard_unit
    return UNIT_MAPPING.get(stripped, stripped)


def _mapped_binary_flag(value: str) -> bool | None:
    if not value:
        return None
    return BINARY_FLAG_MAPPING.get(value.strip().lower())


def _boolean_from_int(value: int) -> bool | None:
    if value in (0, 1):
        return bool(value)
    return None


def _boolean_from_float(value: float) -> bool | None:
    if value in (0.0, 1.0):
        return bool(int(value))
    return None


def normalize_boolean(
    value: Any,  # Any: Accepts various input types for boolean conversion
) -> bool | None:
    """Coerce common source-system boolean encodings to canonical bool."""
    vt = type(value)
    if vt is bool:
        return value
    if vt is str:
        return _mapped_binary_flag(value)
    if vt is int:
        return _boolean_from_int(value)
    if vt is float:
        return _boolean_from_float(value)
    return None


def _flag_from_text(value: str) -> int | None:
    mapped = _mapped_binary_flag(value)
    if mapped is None:
        return None
    return int(mapped)


def _flag_from_int(value: int) -> int | None:
    if value in (0, 1):
        return value
    return None


def _flag_from_float(value: float) -> int | None:
    if value in (0.0, 1.0):
        return int(value)
    return None


def normalize_binary_flag(
    value: Any,  # Any: Handles various input representations for binary flags
) -> int | None:
    """Coerce common boolean-like values to the canonical 0/1 flag contract."""
    vt = type(value)
    if vt is bool:
        return int(value)
    if vt is int:
        return _flag_from_int(value)
    if vt is str:
        return _flag_from_text(value)
    if vt is float:
        return _flag_from_float(value)
    return None


def normalize_operator(
    value: Any,  # Any: Accepts various input types for operator normalization
    allowed_values: frozenset[str] | None = None,
) -> str | None:
    """Canonicalize comparison operators, including Unicode variants."""
    if value is None:
        return None
    stripped = str(value).strip()
    if not stripped:
        return None
    operator = OPERATOR_MAPPING.get(stripped.lower(), stripped)
    if allowed_values is not None and operator not in allowed_values:
        return None
    return operator


def normalize_null(
    value: Any,  # Any: Generic input value from various sources
) -> Any:  # Any: Generic return type to preserve original value type
    """Convert pseudo-null values to proper None values."""
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped or stripped.upper() in _NULL_PATTERNS_UPPER:
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
    if strategy not in strategy_map:
        raise ValidationError(f"Unknown case strategy: {strategy!r}", field="strategy")
    return strategy_map[strategy]


def normalize_cross_pipeline_case(
    value: object, strategy: str = "uppercase"
) -> str | None:
    """Normalize case using one consistent strategy across pipelines."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return _apply_case_strategy(stripped, strategy)
