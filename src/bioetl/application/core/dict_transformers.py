"""Common transformation utilities for all pipelines.

Implements shared transformation patterns to reduce duplication
across ChEMBL and other transformers.

Functions:
- flatten_nested_dict: Flatten nested dicts with a key prefix
- extract_list_field: Extract a field from a list of dicts
- aggregate_nested_lists: Aggregate nested lists
- normalize_string: Normalize string fields (delegated to domain)
- parse_date_field: Parse date with error handling (delegated to domain)
- validate_smiles: Validate a SMILES string (delegated to domain)

Note: Business logic functions are delegated to domain layer per REFACTOR-004.
"""

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
    """Flatten a nested dict into a flat structure with a key prefix.

    Used to extract fields from nested API structures
    (molecule_properties, molecule_hierarchy, ligand_efficiency, etc.).

    Args:
        data: Nested dict to flatten. If None, returns a dict with None
              values for all keys.
        prefix: Prefix for resulting keys (e.g., "property_", "hierarchy_").
        field_mapping: Dict of {source_key: converter}.
                       Converter can be safe_float, safe_int, or None (no conversion).
        renames: Optional dict of {old_key: new_key} for renaming fields
                 after flattening. Keys must include the prefix.

    Returns:
        Flat dict with prefixed and converted values.

    Example:
        >>> data = {"alogp": "3.5", "hba": 2}
        >>> mapping = {"alogp": safe_float, "hba": safe_int}
        >>> flatten_nested_dict(data, "property_", mapping)
        {'property_alogp': 3.5, 'property_hba': 2}

        >>> flatten_nested_dict(None, "property_", mapping)
        {'property_alogp': None, 'property_hba': None}

        >>> # With renames parameter
        >>> data = {"molecule_chembl_id": "CHEMBL25"}
        >>> mapping = {"molecule_chembl_id": None}
        >>> renames = {"hierarchy_molecule_chembl_id": "hierarchy_child_chembl_id"}
        >>> flatten_nested_dict(data, "hierarchy_", mapping, renames)
        {'hierarchy_child_chembl_id': 'CHEMBL25'}

    """
    # Optimized for speed: Single-pass iteration merging prefixing and renaming.
    # Uses explicit type annotation for mypy strict mode.
    result: JsonDict = {}  # Any: dict values vary by field type

    if not data or not isinstance(data, dict):
        for key in field_mapping:
            full_key = f"{prefix}{key}"
            final_key = renames.get(full_key, full_key) if renames else full_key
            result[final_key] = None
        return result

    for source_key, converter in field_mapping.items():
        # Construct the full key once
        full_key = f"{prefix}{source_key}"
        # Determine the final key (handle rename immediately)
        final_key = renames.get(full_key, full_key) if renames else full_key

        value = data.get(source_key)
        if converter is not None and value is not None:
            result[final_key] = converter(value)
        else:
            result[final_key] = value

    return result


def extract_list_field(
    items: list[JsonDict] | None,  # Any: dict values vary by field type
    field: str,
    converter: Callable[[object], T]  # object: converter accepts heterogeneous input
    | None = None,
) -> list[T] | None:
    """Extract field values from a list of dicts.

    Used to aggregate fields from components, classifications, etc.

    Args:
        items: List of dicts to process.
        field: Name of the field to extract.
        converter: Optional converter (safe_int, safe_float, etc.).
                   If None, values are returned as-is.

    Returns:
        List of values, or None if the result is empty.

    Example:
        >>> items = [{"id": "1"}, {"id": "2"}, {"id": None}]
        >>> extract_list_field(items, "id")
        ['1', '2']

        >>> extract_list_field(items, "id", safe_int)
        [1, 2]

    """
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
    """Aggregate nested lists from a list of dicts.

    Used to collect synonyms, xrefs, and other nested lists
    from multiple components into a single flat list.

    Args:
        items: List of dicts, each of which may contain a nested list.
        field: Name of the field containing the nested list.
        deduplicate: If True, removes duplicates from the resulting list (default True).

    Returns:
        Merged list, or None if the result is empty.

    Example:
        >>> items = [
        ...     {"synonyms": ["a", "b"]},
        ...     {"synonyms": ["c", "a"]},
        ...     {"other": "data"}
        ... ]
        >>> aggregate_nested_lists(items, "synonyms")
        ['a', 'b', 'c']

    """
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
    """Normalize a string field.

    Strips leading/trailing whitespace and returns None for empty strings.

    Note: Delegated to domain.normalization.normalize_string per REFACTOR-004.

    Args:
        value: String to normalize.

    Returns:
        Normalized string, or None.

    Example:
        >>> normalize_string("  hello world  ")
        'hello world'
        >>> normalize_string("   ")
        None
        >>> normalize_string(None)
        None

    """
    normalized_value: str | None = _domain_normalize_string(value)
    return normalized_value


def parse_date_field(
    value: str | None,
    fmt: str = "%Y-%m-%d",
) -> date | None:
    """Parse a date string into a date object.

    Safe parsing with error handling for invalid formats.

    Note: Delegated to domain.normalization.parse_date_field per REFACTOR-004.

    Args:
        value: Date string, or None.
        fmt: Date format (default ISO: YYYY-MM-DD).

    Returns:
        A date object, or None on parsing failure.

    Example:
        >>> parse_date_field("2024-01-15")
        datetime.date(2024, 1, 15)
        >>> parse_date_field("invalid")
        None
        >>> parse_date_field("15/01/2024", "%d/%m/%Y")
        datetime.date(2024, 1, 15)

    """
    parsed_value: date | None = _domain_parse_date_field(value, fmt)
    return parsed_value


def validate_smiles(smiles: str | None) -> bool:
    """Validate a SMILES string.

    Performs basic syntax validation without full molecule parsing.
    For full validation, use RDKit or another chemistry library.

    Note: Delegated to domain.validation.validate_smiles per REFACTOR-004.

    Args:
        smiles: SMILES string to validate.

    Returns:
        True if the string matches basic SMILES syntax.

    Example:
        >>> validate_smiles("CCO")  # Ethanol
        True
        >>> validate_smiles("C1=CC=CC=C1")  # Benzene
        True
        >>> validate_smiles("")
        False
        >>> validate_smiles(None)
        False
        >>> validate_smiles("invalid smiles with spaces")
        False

    """
    is_valid: bool = _domain_validate_smiles(smiles)
    return is_valid


def safe_extract(
    record: JsonDict,  # Any: dict values vary by field type
    key: str,
    default: T | None = None,
) -> T | object | None:  # object: dict value type unknown at extraction time
    """Safely extract a value from a dict with logging support.

    Wrapper around dict.get() for unified field extraction.
    For logging, use in combination with a pipeline context.

    Args:
        record: Dict to extract from.
        key: Key to look up.
        default: Default value (None).

    Returns:
        Value for the key, or default.

    Example:
        >>> record = {"name": "test", "value": 42}
        >>> safe_extract(record, "name")
        'test'
        >>> safe_extract(record, "missing", "default")
        'default'

    """
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
