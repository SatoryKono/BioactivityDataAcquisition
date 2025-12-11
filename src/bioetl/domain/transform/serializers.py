"""Serialization utilities for domain entities."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from typing import Any, Literal


def serialize_list(value: Any) -> Any:
    """Serialize a list of primitives or dicts into a pipe-delimited string.

    - Primitives are converted to strings and joined with '|'
    - Dict items are serialized via `serialize_dict`
    - Nested lists/tuples/sequences are skipped
    - None or empty lists yield `pd.NA`
    """
    if value is None:
        return ""

    if isinstance(value, (list, tuple, set, frozenset, Sequence)) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        parts: list[str] = []
        for item in value:
            if item is None or _is_missing(item):
                continue
            if isinstance(item, Mapping):
                dict_str = serialize_dict(item)
                if dict_str:
                    parts.append(dict_str)
                continue
            if isinstance(
                item, (list, tuple, set, frozenset, Sequence)
            ) and not isinstance(item, (str, bytes, bytearray)):
                # Explicitly skip nested sequences
                continue
            parts.append(str(item))

        return "|".join(parts) if parts else ""

    # Non-sequence values: treat None as NA, otherwise convert to string
    return "" if _is_missing(value) else str(value)


def serialize_dict(value: Any) -> Any:
    """Serialize a dict of primitives into a pipe-delimited 'k:v' string.

    - Keys are sorted for determinism
    - Values that are None, NaN or nested structures are skipped
    - None or empty dict yields `pd.NA`
    """
    if value is None:
        return ""

    if not isinstance(value, Mapping):
        # Non-dict values are not supported here; fall back to NA if missing
        return "" if _is_missing(value) else str(value)

    if not value:
        return ""

    parts: list[str] = []
    for key in sorted(value.keys()):
        v = value[key]
        if v is None or _is_missing(v):
            continue
        if isinstance(v, Mapping):
            # Skip nested mappings for this serializer
            continue
        if isinstance(v, (list, tuple, set, frozenset, Sequence)) and not isinstance(
            v, (str, bytes, bytearray)
        ):
            # Skip nested sequences
            continue
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
    if value is None:
        return True
    try:
        return bool(value != value)
    except (TypeError, ValueError):
        return False


__all__ = ["serialize_list", "serialize_dict", "serialize_nested"]
