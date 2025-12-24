"""Common transformation utilities for all pipelines.

Provides reusable functions to reduce duplication across transformers:
- Field extraction and flattening from nested structures
- List field operations (extraction, aggregation)
- String normalization
- Date parsing
- SMILES validation

These utilities are pure functions (no I/O, no side effects).
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, TypeVar

from bioetl.domain.transformations import safe_float, safe_int

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

T = TypeVar("T")


def safe_extract(
    record: dict[str, Any],
    key: str,
    default: T | None = None,
    *,
    strip_strings: bool = True,
) -> Any | T | None:
    """Safely extract value from record with optional string normalization.

    Args:
        record: Source dictionary to extract from.
        key: Key to extract.
        default: Default value if key is missing or value is None.
        strip_strings: If True, strip whitespace from string values.

    Returns:
        Extracted value, normalized if string, or default if missing/None.

    Example:
        >>> safe_extract({"name": "  test  "}, "name")
        'test'
        >>> safe_extract({}, "missing", "default")
        'default'
    """
    value = record.get(key)
    if value is None:
        return default

    if strip_strings and isinstance(value, str):
        value = value.strip()
        return value if value else default

    return value


def normalize_string_field(value: str | None) -> str | None:
    """Strip and normalize string fields.

    Removes leading/trailing whitespace and collapses multiple
    internal spaces to single space.

    Args:
        value: String to normalize.

    Returns:
        Normalized string or None if empty/None.

    Example:
        >>> normalize_string_field("  hello   world  ")
        'hello world'
        >>> normalize_string_field("")
        None
    """
    if value is None:
        return None

    # Strip and collapse multiple spaces
    normalized = " ".join(value.split())
    return normalized if normalized else None


def parse_date_field(
    value: str | None,
    fmt: str = "%Y-%m-%d",
    *,
    fallback_formats: tuple[str, ...] | None = None,
) -> date | None:
    """Parse date field with error handling.

    Attempts to parse date using primary format, then fallback formats.

    Args:
        value: Date string to parse.
        fmt: Primary date format (default: ISO format).
        fallback_formats: Additional formats to try if primary fails.

    Returns:
        Parsed date or None if parsing fails.

    Example:
        >>> parse_date_field("2024-01-15")
        datetime.date(2024, 1, 15)
        >>> parse_date_field("15/01/2024", fmt="%d/%m/%Y")
        datetime.date(2024, 1, 15)
    """
    if not value or not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    formats = [fmt]
    if fallback_formats:
        formats.extend(fallback_formats)

    for date_format in formats:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue

    return None


# SMILES validation regex - basic check for valid characters
# Full validation would require RDKit or similar cheminformatics library
_SMILES_PATTERN = re.compile(
    r"^[A-Za-z0-9@+\-\[\]\(\)\\/#%=.:]+$"
)


def validate_smiles(smiles: str | None) -> bool:
    """Validate SMILES string format.

    Performs basic format validation. Does NOT validate chemical correctness -
    that would require a cheminformatics library like RDKit.

    Args:
        smiles: SMILES string to validate.

    Returns:
        True if SMILES passes basic format validation.

    Example:
        >>> validate_smiles("CCO")  # Ethanol
        True
        >>> validate_smiles("invalid smiles!")
        False
    """
    if not smiles or not isinstance(smiles, str):
        return False

    smiles = smiles.strip()
    if not smiles:
        return False

    # Basic format check
    return bool(_SMILES_PATTERN.match(smiles))


def extract_and_flatten_fields(
    data: dict[str, Any] | None,
    field_mappings: Mapping[str, tuple[str, Callable[..., Any] | None]],
) -> dict[str, Any]:
    """Extract and flatten fields from nested dict with type conversion.

    Transforms a nested dictionary by extracting specified fields with
    optional type conversion, producing a flat dictionary with new keys.

    Args:
        data: Source dictionary (can be None).
        field_mappings: Dict mapping output_key -> (source_key, converter).
            converter can be None for direct copy, or a callable like
            safe_float, safe_int, str, etc.

    Returns:
        Flat dictionary with mapped fields. All keys will be present,
        with None values for missing or failed conversions.

    Example:
        >>> data = {"parent_id": "123", "value": "45.6"}
        >>> mappings = {
        ...     "hierarchy_parent_id": ("parent_id", str),
        ...     "hierarchy_value": ("value", safe_float),
        ... }
        >>> extract_and_flatten_fields(data, mappings)
        {'hierarchy_parent_id': '123', 'hierarchy_value': 45.6}

        >>> extract_and_flatten_fields(None, mappings)
        {'hierarchy_parent_id': None, 'hierarchy_value': None}
    """
    result: dict[str, Any] = {}

    if not data or not isinstance(data, dict):
        # Return template with None values
        return dict.fromkeys(field_mappings, None)

    for out_key, (source_key, converter) in field_mappings.items():
        value = data.get(source_key)
        if value is None:
            result[out_key] = None
        elif converter is not None:
            result[out_key] = converter(value)
        else:
            result[out_key] = value

    return result


def extract_list_field(
    items: list[dict[str, Any]] | None,
    field: str,
    *,
    converter: Callable[[Any], T] | None = None,
    filter_none: bool = True,
) -> list[T] | None:
    """Extract a single field from a list of dictionaries.

    Iterates over a list of dicts, extracting one field from each,
    with optional type conversion.

    Args:
        items: List of dictionaries to extract from.
        field: Field name to extract from each dict.
        converter: Optional type converter (e.g., safe_int, safe_float).
        filter_none: If True, exclude None values from result.

    Returns:
        List of extracted values, or None if empty/no valid values.

    Example:
        >>> items = [{"id": 1}, {"id": 2}, {"id": None}]
        >>> extract_list_field(items, "id")
        [1, 2]
        >>> extract_list_field(items, "id", filter_none=False)
        [1, 2, None]
        >>> extract_list_field(items, "id", converter=str)
        ['1', '2']
    """
    if not items or not isinstance(items, list):
        return None

    values: list[Any] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        value = item.get(field)

        if filter_none and value is None:
            continue

        if converter is not None and value is not None:
            converted = converter(value)
            if filter_none and converted is None:
                continue
            values.append(converted)
        else:
            values.append(value)

    return values if values else None


def aggregate_nested_list(
    items: list[dict[str, Any]] | None,
    nested_field: str,
) -> list[Any] | None:
    """Aggregate nested lists from a list of dictionaries.

    Collects all items from a nested list field across multiple dicts
    into a single flat list.

    Args:
        items: List of dictionaries to aggregate from.
        nested_field: Field name containing nested list in each dict.

    Returns:
        Aggregated flat list, or None if empty.

    Example:
        >>> items = [
        ...     {"synonyms": ["a", "b"]},
        ...     {"synonyms": ["c"]},
        ...     {"synonyms": None},
        ... ]
        >>> aggregate_nested_list(items, "synonyms")
        ['a', 'b', 'c']
    """
    if not items or not isinstance(items, list):
        return None

    aggregated: list[Any] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        nested = item.get(nested_field)
        if nested and isinstance(nested, list):
            aggregated.extend(nested)

    return aggregated if aggregated else None


def extract_nested_field_values(
    items: list[dict[str, Any]] | None,
    nested_field: str,
    value_field: str,
    *,
    converter: Callable[[Any], T] | None = None,
) -> list[T] | None:
    """Extract values from nested lists within a list of dicts.

    For structures like:
    [
        {"classifications": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]},
        {"classifications": [{"id": 3, "name": "C"}]}
    ]

    Args:
        items: List of dictionaries containing nested lists.
        nested_field: Field containing nested list in each dict.
        value_field: Field to extract from each nested dict.
        converter: Optional type converter for extracted values.

    Returns:
        Flat list of extracted values, or None if empty.

    Example:
        >>> items = [
        ...     {"classes": [{"id": 1}, {"id": 2}]},
        ...     {"classes": [{"id": 3}]},
        ... ]
        >>> extract_nested_field_values(items, "classes", "id")
        [1, 2, 3]
    """
    if not items or not isinstance(items, list):
        return None

    values: list[Any] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        nested_list = item.get(nested_field)
        if not nested_list or not isinstance(nested_list, list):
            continue

        for nested_item in nested_list:
            if not isinstance(nested_item, dict):
                continue

            value = nested_item.get(value_field)
            if value is None:
                continue

            if converter is not None:
                converted = converter(value)
                if converted is not None:
                    values.append(converted)
            else:
                values.append(value)

    return values if values else None


def build_empty_field_dict(field_names: list[str]) -> dict[str, None]:
    """Build a dictionary with given field names, all set to None.

    Utility for creating empty result templates.

    Args:
        field_names: List of field names.

    Returns:
        Dict with all fields set to None.

    Example:
        >>> build_empty_field_dict(["id", "name", "value"])
        {'id': None, 'name': None, 'value': None}
    """
    return dict.fromkeys(field_names, None)


# Re-export safe_float and safe_int for convenience
__all__ = [
    "aggregate_nested_list",
    "build_empty_field_dict",
    "extract_and_flatten_fields",
    "extract_list_field",
    "extract_nested_field_values",
    "normalize_string_field",
    "parse_date_field",
    "safe_extract",
    "safe_float",
    "safe_int",
    "validate_smiles",
]
