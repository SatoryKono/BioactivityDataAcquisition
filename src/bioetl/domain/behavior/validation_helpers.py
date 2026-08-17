"""Validation helpers module for common validation operations."""

from __future__ import annotations

import json

from bioetl.domain.types import JsonDict


def validate_data(data: object) -> None:
    """Validate that data is present (None / empty collections only).

    Numeric zero and boolean False are valid payloads and must not fail.

    Args:
        data: Data to validate.

    Raises:
        ValueError: If data is None or an empty collection/string.
    """
    if data is None or (
        isinstance(
            data, (str, bytes, bytearray, list, tuple, set, frozenset, dict, range)
        )
        and len(data) == 0
    ):
        raise ValueError("Data is empty")


def aggregation_field_name(entry: object) -> str | None:
    """Return a field name from a string or mapping descriptor."""
    if isinstance(entry, str):
        return entry
    if not isinstance(entry, dict):
        return None
    name = entry.get("name")
    return name if isinstance(name, str) and name else None


def aggregation_field_names_from_list(fields_node: list[object]) -> set[str]:
    """Extract field names from string entries or dict descriptors."""
    names = (aggregation_field_name(entry) for entry in fields_node)
    return {name for name in names if name is not None}


def _aggregation_column_name(entry: object) -> str | None:
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return aggregation_field_name(entry)
    return None


def _aggregation_column_names(columns: object) -> set[str]:
    if not isinstance(columns, list):
        return set()
    names = (_aggregation_column_name(entry) for entry in columns)
    return {name for name in names if name is not None}


def _explicit_field_names(names: object) -> set[str]:
    if not isinstance(names, list):
        return set()
    return {item for item in names if isinstance(item, str)}


def aggregation_fallback_fields(source_schema: JsonDict) -> set[str]:
    """Collect field names from explicit fallback schema shapes."""
    fields = _aggregation_column_names(source_schema.get("columns"))
    fields.update(_explicit_field_names(source_schema.get("field_names")))
    return fields


def aggregation_source_fields(source_schema: JsonDict) -> set[str]:
    """Extract source fields from supported schema representations."""
    properties = source_schema.get("properties")
    if isinstance(properties, dict):
        return set(properties.keys())
    fields_node = source_schema.get("fields")
    if isinstance(fields_node, list):
        return aggregation_field_names_from_list(fields_node)
    return aggregation_fallback_fields(source_schema)


def aggregation_group_key(
    record: JsonDict, group_by_fields: list[str]
) -> tuple[tuple[str, str, str], ...]:
    """Build a type-preserving group key for aggregation validation."""
    components: list[tuple[str, str, str]] = []
    for field in group_by_fields:
        if field not in record:
            components.append(("absent", "", ""))
            continue
        value = record[field]
        type_name = type(value).__name__
        if value is None:
            components.append(("present", "NoneType", "null"))
        else:
            components.append(
                (
                    "present",
                    type_name,
                    json.dumps(
                        value,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ),
                )
            )
    return tuple(components)
