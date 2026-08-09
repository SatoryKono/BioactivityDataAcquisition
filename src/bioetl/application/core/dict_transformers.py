"""Shared record-transformation helpers reused across pipeline implementations."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import TypeVar

from bioetl.domain.normalization import normalize_string as _domain_normalize_string
from bioetl.domain.normalization import parse_date_field as _domain_parse_date_field
from bioetl.domain.transformations import safe_float, safe_int
from bioetl.domain.types import JsonDict
from bioetl.domain.validation import validate_smiles as _domain_validate_smiles

T = TypeVar("T")


def flatten_nested_dict(
    data: JsonDict | None,  # Any: dict values vary by field type
    prefix: str,
    field_mapping: dict[
        str, Callable[[object], object] | None  # object: heterogeneous record values
    ],
    renames: dict[str, str] | None = None,
) -> JsonDict:  # Any: dict values vary by field type
    """Flatten one nested mapping into prefixed output fields."""
    result: JsonDict = {}  # Any: dict values vary by field type
    if not data or not isinstance(data, dict):
        for key in field_mapping:
            full_key = f"{prefix}{key}"
            final_key = renames.get(full_key, full_key) if renames else full_key
            result[final_key] = None
        return result
    for source_key, converter in field_mapping.items():
        full_key = f"{prefix}{source_key}"
        final_key = renames.get(full_key, full_key) if renames else full_key
        value = data.get(source_key)
        if converter is not None and value is not None:
            result[final_key] = converter(value)
        else:
            result[final_key] = value
    return result


def extract_list_field[T](
    items: list[JsonDict] | None,  # Any: dict values vary by field type
    field: str,
    converter: Callable[[object], T]  # object: converter accepts heterogeneous input
    | None = None,
) -> list[T] | None:
    """Extract one field from a list of dict-like items."""
    if not items or not isinstance(items, list):
        return None
    values: list[T] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_value = item.get(field)
        if raw_value is None:
            continue
        if converter is not None:
            converted = converter(raw_value)
            if converted is not None:
                values.append(converted)
        else:
            values.append(raw_value)
    return values if values else None


def _extract_nested_values(
    items: list[JsonDict],  # Any: dict values vary by field type
    field: str,
) -> list[object]:  # object: nested list elements have heterogeneous types
    """Extract all nested list values from a field across items."""
    values: list[object] = []  # object: nested list elements have heterogeneous types
    for item in items:
        if isinstance(item, dict):
            nested = item.get(field)
            if isinstance(nested, list):
                values.extend(nested)
    return values


def aggregate_nested_lists(
    items: list[JsonDict] | None,  # Any: dict values vary by field type
    field: str,
    deduplicate: bool = True,
) -> list[object] | None:  # object: nested list elements have heterogeneous types
    """Merge nested list values from a list of mapping-like items."""
    if not isinstance(items, list) or not items:
        return None
    values = _extract_nested_values(items, field)
    if not values:
        return None
    if deduplicate:
        seen: set[str] = set()
        unique: list[
            object
        ] = []  # object: nested list elements have heterogeneous types
        for val in values:
            key = str(val)
            if key not in seen:
                seen.add(key)
                unique.append(val)
        return unique if unique else None
    return values


def normalize_string(value: str | None) -> str | None:
    """Normalize one string value via the domain normalization seam."""
    normalized_value: str | None = _domain_normalize_string(value)
    return normalized_value


def parse_date_field(
    value: str | None,
    fmt: str = "%Y-%m-%d",
) -> date | None:
    """Parse one date value via the domain normalization seam."""
    parsed_value: date | None = _domain_parse_date_field(value, fmt)
    return parsed_value


def validate_smiles(smiles: str | None) -> bool:
    """Validate one SMILES string via the domain validation seam."""
    is_valid: bool = _domain_validate_smiles(smiles)
    return is_valid


def safe_extract[T](
    record: JsonDict,  # Any: dict values vary by field type
    key: str,
    default: T | None = None,
) -> T | object | None:  # object: dict value type unknown at extraction time
    """Read one value from a mapping with a uniform extraction helper."""
    extracted_value: T | object | None = record.get(key, default)
    return extracted_value


# Re-export safe_float and safe_int for convenience
__all__ = [
    "aggregate_nested_lists",
    "extract_list_field",
    "flatten_nested_dict",
    "normalize_string",
    "parse_date_field",
    "safe_extract",
    "safe_float",
    "safe_int",
    "validate_smiles",
]
