"""Normalization rules for case handling and unit canonicalization."""

from __future__ import annotations

from typing import Any

from bioetl.domain.normalization.text import normalize_string

__all__ = [
    "normalize_case",
    "normalize_cross_pipeline_case",
    "normalize_null",
    "normalize_unit",
    "NULL_PATTERNS",
    "UNIT_MAPPING",
]

# Pseudo-null patterns to convert to None
NULL_PATTERNS: frozenset[str] = frozenset(
    [
        "N/A",
        "NA",
        "n/a",
        "na",
        "None",
        "NONE",
        "none",
        "Null",
        "NULL",
        "null",
        "-",
        "--",
        ".",
        "..",
        "...",
        "",
        " ",
        "  ",
        "   ",
        "\t",
        "\n",
        "\r",
        "\r\n",
        "<NA>",
        "<na>",
        "<NULL>",
        "<null>",
        "NAN",
        "NaN",
        "nan",
        "NULL_VALUE",
        "NULL_VALUE",
        "MISSING",
        "missing",
        "UNKNOWN",
        "unknown",
        "NOT_AVAILABLE",
        "not_available",
        "NOT_APPLICABLE",
        "not_applicable",
        "N/A",  # Duplicate for emphasis
        "NA",  # Duplicate for emphasis
    ]
)


# Unit canonicalization mapping
UNIT_MAPPING: dict[str, str] = {
    # Nanoliter variations
    "nL": "nL",
    "NL": "nL",
    "nl": "nL",
    # Microliter variations
    "uL": "µL",
    "UL": "µL",
    "µL": "µL",
    # Milliliter variations
    "mL": "mL",
    "ML": "mL",
    "ml": "mL",
    # Liter variations
    "L": "L",
    "l": "L",
    # Nanomolar variations (most common for bioactivity)
    "nM": "nM",
    "NM": "nM",
    "nm": "nM",
    # Micromolar variations
    "uM": "µM",
    "UM": "µM",
    "µM": "µM",
    "μM": "µM",
    # Millimolar variations
    "mM": "mM",
    "MM": "mM",
    "mm": "mM",
    # Molar variations
    "M": "M",
    "m": "M",
    # Picomolar variations
    "pM": "pM",
    "PM": "pM",
    "pm": "pM",
    # Gram variations
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
    # Percentage variations
    "%": "%",
    "percent": "%",
    "PERCENT": "%",
    # Other common units
    "U": "U",
    "u": "U",
    "units": "U",
    "UNITS": "U",
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
    """Normalize case for enum-like fields.

    Args:
        value: The value to normalize
        allowed_values: Optional set of allowed values for validation

    Returns:
        Normalized value (case-preserved from allowed_values) if valid, None otherwise
    """
    if value is None or not isinstance(value, str):
        return None

    # Normalize string first (trim whitespace, etc.)
    normalized = normalize_string(value)
    if normalized is None:
        return None

    # Handle validation against allowed values
    if allowed_values is not None:
        return _find_case_match(normalized, allowed_values)

    # No allowed_values provided, just normalize string
    return normalized


def normalize_unit(
    value: Any,  # Any: Generic input value from various sources
) -> str | None:
    """Canonicalize unit strings to standard format.

    Args:
        value: The unit value to normalize

    Returns:
        Canonical unit string or None if invalid
    """
    if value is None:
        return None

    if not isinstance(value, str):
        return None

    # Normalize string first
    normalized = normalize_string(value)
    if normalized is None:
        return None

    # Apply unit mapping
    return UNIT_MAPPING.get(normalized, normalized)


def normalize_null(
    value: Any,  # Any: Generic input value from various sources
) -> Any:  # Any: Generic return type to preserve original value type
    """Convert pseudo-null values to proper None values.

    Args:
        value: The value to check for null patterns

    Returns:
        None if value matches null patterns, original value otherwise
    """
    if value is None:
        return None

    if not isinstance(value, str):
        return value

    # Normalize string first (trim whitespace, etc.)
    normalized = normalize_string(value)
    if normalized is None:
        return None

    # Check against null patterns
    if normalized in NULL_PATTERNS:
        return None

    return value


def normalize_enum_case(
    value: Any,  # Any: Generic input value from various sources
    allowed_values: frozenset[str],
) -> str | None:
    """Normalize enum value with case normalization and validation.

    This is a specialized version for enum fields that combines
    case normalization with enum validation.

    Args:
        value: The value to normalize
        allowed_values: Set of allowed enum values

    Returns:
        Normalized uppercase value if valid, None otherwise
    """
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
    """Normalize case using consistent strategy across all pipelines.

    This function provides a unified approach to case normalization that can be
    applied consistently across all ChEMBL pipelines. Unlike normalize_case which
    is designed for enum validation, this function focuses on applying standardized
    case strategies to any string field.

    Args:
        value: The value to normalize
        strategy: Case strategy to apply ("uppercase", "lowercase", or "preserve")

    Returns:
        Normalized value according to strategy, or None if invalid

    Examples:
        >>> normalize_cross_pipeline_case("ic50", "uppercase")
        "IC50"
        >>> normalize_cross_pipeline_case("In Vivo", "lowercase")
        "in vivo"
        >>> normalize_cross_pipeline_case("Cell Culture", "preserve")
        "Cell Culture"
    """
    if value is None or not isinstance(value, str):
        return None

    # Normalize string first (trim whitespace, etc.)
    normalized = normalize_string(value)
    if normalized is None:
        return None

    return _apply_case_strategy(normalized, strategy)
