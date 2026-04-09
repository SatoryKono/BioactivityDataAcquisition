"""Private normalization helpers for deterministic content hashing."""

from __future__ import annotations

import math
from datetime import date, datetime
from functools import singledispatch
from typing import Any  # Any: singledispatch requires Any for dispatch

from bioetl.domain.normalization.json import deserialize_json_value
from bioetl.domain.types import JsonDict

from ..serialization import serialize_to_canonical_json


@singledispatch
def _normalize_value(
    value: Any,  # Any: singledispatch requires Any for dispatch
) -> Any:  # Any: singledispatch requires Any for dispatch
    """Normalize a single value using singledispatch."""
    return value


@_normalize_value.register(float)
def _normalize_float(value: float) -> float | None:
    """Normalize a float value, handling NaN/Inf."""
    if math.isnan(value) or math.isinf(value):
        return None
    return round(value, 10)


@_normalize_value.register(datetime)
def _normalize_datetime(value: datetime) -> str:
    """Normalize datetime to date ISO string."""
    return value.date().isoformat()


@_normalize_value.register(date)
def _normalize_date(value: date) -> str:
    """Normalize date to ISO string."""
    return value.isoformat()


@_normalize_value.register(str)
def _normalize_str(value: str) -> str:
    """Normalize string by stripping whitespace."""
    return value.strip()


@_normalize_value.register(dict)
def _normalize_dict(value: JsonDict) -> JsonDict:
    """Normalize dict by recursively normalizing values."""
    return {k: _normalize_value(v) for k, v in value.items()}


@_normalize_value.register(list)
def _normalize_list(value: list[object]) -> list[object]:
    """Normalize list by recursively normalizing elements."""
    return [_normalize_value(v) for v in value]


def _maybe_deserialize_json_string(value: str) -> object:
    if not _looks_like_serialized_json_container(value):
        return value
    stripped = value.strip()
    try:
        return deserialize_json_value(stripped)
    except ValueError:
        return value


def _looks_like_serialized_json_container(value: str) -> bool:
    stripped = value.strip()
    if len(stripped) < 2:
        return False
    return (
        (stripped.startswith("{") and stripped.endswith("}"))
        or (stripped.startswith("[") and stripped.endswith("]"))
    )


def _canonical_sort_key(value: object) -> str:
    return serialize_to_canonical_json({"value": value})


def _sort_normalized_sequence(values: list[object]) -> list[object]:
    return sorted(values, key=_canonical_sort_key)


def _normalize_hash_mapping(
    value: JsonDict,
    *,
    sort_nested_sequences: bool,
) -> JsonDict:
    return {
        key: _normalize_value_for_hash(
            item,
            sort_nested_sequences=sort_nested_sequences,
        )
        for key, item in value.items()
    }


def _normalize_hash_sequence(
    values: list[object],
    *,
    sort_nested_sequences: bool,
) -> list[object]:
    normalized = [
        _normalize_value_for_hash(
            item,
            sort_nested_sequences=sort_nested_sequences,
        )
        for item in values
    ]
    if sort_nested_sequences:
        return _sort_normalized_sequence(normalized)
    return normalized


def _normalize_hash_set_like(value: set[object] | frozenset[object]) -> list[object]:
    normalized = _normalize_hash_sequence(
        list(value),
        sort_nested_sequences=False,
    )
    return _sort_normalized_sequence(normalized)


def _normalize_hash_collection(
    value: object,
    *,
    sort_nested_sequences: bool,
) -> object:
    if isinstance(value, list):
        return _normalize_hash_sequence(
            value,
            sort_nested_sequences=sort_nested_sequences,
        )
    if isinstance(value, tuple):
        return _normalize_hash_sequence(
            list(value),
            sort_nested_sequences=sort_nested_sequences,
        )
    if isinstance(value, (set, frozenset)):
        return _normalize_hash_set_like(value)
    return _NO_NORMALIZED_COLLECTION


def _normalize_hash_scalar(
    value: object,
    *,
    sort_nested_sequences: bool,
) -> object:
    if not sort_nested_sequences or not isinstance(value, str):
        return _normalize_value(value)
    candidate = _maybe_deserialize_json_string(value)
    if candidate is value:
        return _normalize_value(value)
    return _normalize_value_for_hash(
        candidate,
        sort_nested_sequences=True,
    )


_NO_NORMALIZED_COLLECTION = object()


def _normalize_value_for_hash(
    value: object,
    *,
    sort_nested_sequences: bool,
) -> object:
    """Normalize one value for deterministic hash generation."""
    if isinstance(value, dict):
        return _normalize_hash_mapping(
            value,
            sort_nested_sequences=sort_nested_sequences,
        )
    collection = _normalize_hash_collection(
        value,
        sort_nested_sequences=sort_nested_sequences,
    )
    if collection is not _NO_NORMALIZED_COLLECTION:
        return collection
    return _normalize_hash_scalar(
        value,
        sort_nested_sequences=sort_nested_sequences,
    )
