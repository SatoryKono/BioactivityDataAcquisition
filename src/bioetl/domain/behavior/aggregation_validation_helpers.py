"""Schema and group-key helpers for aggregation validation."""

from __future__ import annotations

import json

from bioetl.domain.types import JsonDict


def collect_duplicate_groups(
    *,
    aggregation_results: list[JsonDict],
    group_by_fields: list[str],
) -> list[JsonDict]:
    """Collect repeated type-preserving group keys."""
    seen_groups: set[tuple[tuple[str, str, str], ...]] = set()
    duplicates: list[JsonDict] = []
    for index, record in enumerate(aggregation_results):
        group_key = build_group_key(record, group_by_fields)
        if group_key in seen_groups:
            duplicates.append(
                {"index": index, "group_key": group_key, "record": record}
            )
        else:
            seen_groups.add(group_key)
    return duplicates


def build_group_key(
    record: JsonDict, group_by_fields: list[str]
) -> tuple[tuple[str, str, str], ...]:
    """Build a type-preserving, canonical grouping key."""
    components: list[tuple[str, str, str]] = []
    for field in group_by_fields:
        if field not in record:
            components.append(("absent", "", ""))
            continue
        value = record[field]
        if value is None:
            components.append(("present", "NoneType", "null"))
        else:
            components.append(
                ("present", type(value).__name__, canonical_group_value(value))
            )
    return tuple(components)


def field_name_from_descriptor(entry: object) -> str | None:
    """Return a field name from a string or mapping descriptor."""
    if isinstance(entry, str):
        return entry
    if not isinstance(entry, dict):
        return None
    name = entry.get("name")
    return name if isinstance(name, str) and name else None


def column_names(columns: object) -> set[str]:
    """Return names from the fallback ``columns`` schema shape."""
    if not isinstance(columns, list):
        return set()
    names = (_column_name(entry) for entry in columns)
    return {name for name in names if name is not None}


def explicit_field_names(names: object) -> set[str]:
    """Return explicit string names from the fallback ``field_names`` shape."""
    if not isinstance(names, list):
        return set()
    return {item for item in names if isinstance(item, str)}


def _column_name(entry: object) -> str | None:
    if isinstance(entry, dict):
        return field_name_from_descriptor(entry)
    return entry if isinstance(entry, str) else None


def canonical_group_value(value: object) -> str:
    """Serialize group values without order- or address-sensitive repr."""
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise TypeError(
            "aggregation group-by values must be JSON-serializable and finite"
        ) from exc
