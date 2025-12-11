"""Serialization utilities for domain entities."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    pass


def _is_sequence(value: Any) -> bool:
    """Check if value is a sequence (but not string/bytes)."""
    return isinstance(value, (list, tuple, set, frozenset, Sequence)) and not isinstance(
        value, (str, bytes, bytearray)
    )


def _serialize_list_item(item: Any) -> str | None:
    """Serialize a single list item, returning None if it should be skipped."""
    if item is None or _is_missing(item):
        return None
    if isinstance(item, Mapping):
        dict_str = serialize_dict(item)
        return dict_str if dict_str and dict_str != "" else None
    if _is_sequence(item):
        return None  # Skip nested sequences
    return str(item)


def serialize_list(value: Any) -> Any:
    """Serialize a list of primitives or dicts into a pipe-delimited string.

    - Primitives are converted to strings and joined with '|'
    - Dict items are serialized via `serialize_dict`
    - Nested lists/tuples/sequences are skipped
    - None or empty lists yield None (infrastructure layer converts to pd.NA)
    """
    if value is None or _is_missing(value):
        return None

    if not _is_sequence(value):
        return None if _is_missing(value) else str(value)

    if not value:
        return None

    parts: list[str] = []
    for item in value:
        serialized = _serialize_list_item(item)
        if serialized is not None:
            parts.append(serialized)

    return "|".join(parts) if parts else None


def _should_skip_dict_value(v: Any) -> bool:
    """Check if dict value should be skipped during serialization."""
    if v is None or _is_missing(v):
        return True
    if isinstance(v, Mapping):
        return True  # Skip nested mappings
    if _is_sequence(v):
        return True  # Skip nested sequences
    return False


def serialize_dict(value: Any) -> Any:
    """Serialize a dict of primitives into a pipe-delimited 'k:v' string.

    - Keys are sorted for determinism
    - Values that are None, NaN or nested structures are skipped
    - None or empty dict yields `pd.NA`
    """
    if value is None:
        return ""

    if not isinstance(value, Mapping):
        return "" if _is_missing(value) else str(value)

    if not value:
        return ""

    parts: list[str] = []
    for key in sorted(value.keys()):
        v = value[key]
        if not _should_skip_dict_value(v):
            parts.append(f"{key}:{str(v)}")

    return "|".join(parts) if parts else ""


def serialize_nested(
    value: Any, *, mode: Literal["json", "flat", "pipe"] = "json"
) -> str:
    """Serialize nested structures deterministically to a string."""

    if _is_missing(value):
        return ""

    if mode not in {"json", "flat", "pipe"}:
        raise ValueError(f"Unsupported serialization mode: {mode}")

    if mode == "json":
        return _serialize_json(value)

    if isinstance(value, Mapping):
        return _serialize_mapping(value, mode)

    if isinstance(value, (set, frozenset)):
        try:
            sorted_value = sorted(value)
        except TypeError:
            sorted_value = sorted(value, key=str)
        return _serialize_sequence(sorted_value, mode)

    if isinstance(value, (list, tuple, Sequence)) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return _serialize_sequence(value, mode)

    return str(value)


def _serialize_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            default=_json_default,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except TypeError:
        return json.dumps(str(value), ensure_ascii=False)


def _json_default(value: Any) -> Any:
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if isinstance(value, Mapping):
        return dict(sorted(value.items()))
    if isinstance(value, (list, tuple, Sequence)) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return list(value)
    return str(value)


def _serialize_mapping(
    mapping: Mapping[str, Any], mode: Literal["json", "flat", "pipe"]
) -> str:
    delimiter = "|" if mode == "pipe" else ","
    kv_separator = ":" if mode == "pipe" else "="
    parts: list[str] = []

    for key in sorted(mapping.keys()):
        serialized_value = serialize_nested(mapping[key], mode=mode)
        if serialized_value == "":
            continue
        parts.append(f"{key}{kv_separator}{serialized_value}")

    return delimiter.join(parts)


def _serialize_sequence(
    seq: Sequence[Any], mode: Literal["json", "flat", "pipe"]
) -> str:
    delimiter = "|" if mode == "pipe" else ","
    parts: list[str] = []

    for item in seq:
        serialized_value = serialize_nested(item, mode=mode)
        if serialized_value == "":
            continue
        parts.append(serialized_value)

    return delimiter.join(parts)


def _is_missing(value: Any) -> bool:
    """Check if value is None or NaN-like (handles pd.NA without importing pandas)."""
    if value is None:
        return True

    # Check for pandas.NA (NAType) without importing pandas
    if type(value).__name__ == "NAType":
        return True

    # Check for NaN-like values
    try:
        return bool(value != value)
    except (TypeError, ValueError):
        return False


__all__ = ["serialize_list", "serialize_dict", "serialize_nested"]
