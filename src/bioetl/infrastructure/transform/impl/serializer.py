"""Serialization utilities for domain entities."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal

import pandas as pd


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

    if isinstance(value, (list, tuple, set, frozenset, Sequence)) and not isinstance(
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


def _serialize_mapping(mapping: Mapping[str, Any], mode: str) -> str:
    delimiter = "|" if mode == "pipe" else ","
    kv_separator = ":" if mode == "pipe" else "="
    parts: list[str] = []

    for key in sorted(mapping.keys()):
        serialized_value = serialize_nested(mapping[key], mode=mode)
        if serialized_value == "":
            continue
        parts.append(f"{key}{kv_separator}{serialized_value}")

    return delimiter.join(parts)


def _serialize_sequence(seq: Sequence[Any], mode: str) -> str:
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
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


__all__ = ["serialize_nested"]
