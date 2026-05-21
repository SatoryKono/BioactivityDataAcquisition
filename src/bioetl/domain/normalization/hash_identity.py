"""Canonical hash-identity normalization for content hashes and dedup identity.

This module defines the explicit domain-owned contract used by:
- ``content_hash`` generation
- content-aware dedup winner selection
- canonical JSON bytes for hash identity material

The semantics here are intentionally narrower than general domain
normalization. In particular, ``datetime`` values collapse to ``date`` ISO
strings to preserve the historical content-hash contract until a deliberate
hash migration is approved.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import UTC, date, datetime
from functools import singledispatch
from typing import Literal

from bioetl.domain.constants import META_FIELDS
from bioetl.domain.normalization.json import (
    deserialize_json_value,
    serialize_json_canonical,
)
from bioetl.domain.types import JsonDict

__all__ = [
    "HashDatetimePolicy", "normalize_hash_identity_record",
    "normalize_hash_identity_value", "serialize_hash_identity_canonical_json",
]

HashDatetimePolicy = Literal["v1_date", "v2_datetime_utc"]


@singledispatch
def _normalize_scalar(
    value: object,
) -> object:
    """Normalize one scalar value for the hash-identity contract."""
    return value


@_normalize_scalar.register(float)
def _normalize_float(value: float) -> float | None:
    """Normalize floats for deterministic hashing and dedup identity."""
    if math.isnan(value) or math.isinf(value):
        return None
    return round(value, 10)


@_normalize_scalar.register(datetime)
def _normalize_datetime(value: datetime) -> str:
    """Collapse datetimes to date ISO strings for the historical hash contract."""
    return value.date().isoformat()


@_normalize_scalar.register(date)
def _normalize_date(value: date) -> str:
    """Normalize dates to ISO strings."""
    return value.isoformat()


@_normalize_scalar.register(str)
def _normalize_str(value: str) -> str:
    """Strip strings before hashing."""
    return value.strip()


def _normalize_datetime_utc(value: datetime) -> str:
    """Normalize datetimes with full UTC precision for v2 hash identity."""
    aware_value = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    utc_value = aware_value.astimezone(UTC)
    return utc_value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _normalize_scalar_for_policy(
    value: object,
    *,
    datetime_policy: HashDatetimePolicy,
) -> object:
    """Normalize one scalar under the selected versioned hash policy."""
    if isinstance(value, datetime) and datetime_policy == "v2_datetime_utc":
        return _normalize_datetime_utc(value)
    return _normalize_scalar(value)


def _looks_like_serialized_json_container(value: str) -> bool:
    stripped = value.strip()
    if len(stripped) < 2:
        return False
    return (stripped.startswith("{") and stripped.endswith("}")) or (
        stripped.startswith("[") and stripped.endswith("]")
    )


def _maybe_deserialize_json_string(value: str) -> object:
    if not _looks_like_serialized_json_container(value):
        return value
    stripped = value.strip()
    try:
        return deserialize_json_value(stripped)
    except ValueError:
        return value


def _canonical_sort_key(value: object) -> str:
    return serialize_json_canonical({"value": value})


def _sort_normalized_sequence(values: list[object]) -> list[object]:
    return sorted(values, key=_canonical_sort_key)


def _normalize_hash_sequence(
    values: list[object],
    *,
    sort_nested_sequences: bool,
    datetime_policy: HashDatetimePolicy,
) -> list[object]:
    normalized = [
        normalize_hash_identity_value(
            item,
            sort_nested_sequences=sort_nested_sequences,
            datetime_policy=datetime_policy,
        )
        for item in values
    ]
    if sort_nested_sequences:
        return _sort_normalized_sequence(normalized)
    return normalized


def _normalize_hash_set_like(
    value: set[object] | frozenset[object],
    *,
    datetime_policy: HashDatetimePolicy,
) -> list[object]:
    normalized = _normalize_hash_sequence(
        list(value),
        sort_nested_sequences=False,
        datetime_policy=datetime_policy,
    )
    return _sort_normalized_sequence(normalized)


def _normalize_hash_mapping(
    value: JsonDict,
    *,
    sort_nested_sequences: bool,
    datetime_policy: HashDatetimePolicy,
) -> JsonDict:
    return {
        key: normalize_hash_identity_value(
            item,
            sort_nested_sequences=sort_nested_sequences,
            datetime_policy=datetime_policy,
        )
        for key, item in value.items()
    }


_NO_NORMALIZED_COLLECTION = object()


def _normalize_hash_collection(
    value: object,
    *,
    sort_nested_sequences: bool,
    datetime_policy: HashDatetimePolicy,
) -> object:
    if isinstance(value, list):
        return _normalize_hash_sequence(
            value,
            sort_nested_sequences=sort_nested_sequences,
            datetime_policy=datetime_policy,
        )
    if isinstance(value, tuple):
        return _normalize_hash_sequence(
            list(value),
            sort_nested_sequences=sort_nested_sequences,
            datetime_policy=datetime_policy,
        )
    if isinstance(value, (set, frozenset)):
        return _normalize_hash_set_like(value, datetime_policy=datetime_policy)
    return _NO_NORMALIZED_COLLECTION


def _normalize_hash_string_candidate(
    value: object,
    *,
    sort_nested_sequences: bool,
    datetime_policy: HashDatetimePolicy,
) -> object | None:
    if not sort_nested_sequences or not isinstance(value, str):
        return None
    candidate = _maybe_deserialize_json_string(value)
    if candidate is value:
        return None
    return normalize_hash_identity_value(
        candidate,
        sort_nested_sequences=True,
        datetime_policy=datetime_policy,
    )


def normalize_hash_identity_value(
    value: object,
    *,
    sort_nested_sequences: bool,
    datetime_policy: HashDatetimePolicy = "v1_date",
) -> object:
    """Normalize one value for deterministic hash identity material."""
    if isinstance(value, dict):
        return _normalize_hash_mapping(
            value,
            sort_nested_sequences=sort_nested_sequences,
            datetime_policy=datetime_policy,
        )

    collection = _normalize_hash_collection(
        value,
        sort_nested_sequences=sort_nested_sequences,
        datetime_policy=datetime_policy,
    )
    if collection is not _NO_NORMALIZED_COLLECTION:
        return collection

    normalized_string_candidate = _normalize_hash_string_candidate(
        value,
        sort_nested_sequences=sort_nested_sequences,
        datetime_policy=datetime_policy,
    )
    if normalized_string_candidate is not None:
        return normalized_string_candidate

    return _normalize_scalar_for_policy(value, datetime_policy=datetime_policy)


def _should_include_hash_identity_field(
    key: str,
    value: object,
    *,
    exclude_none: bool,
    include_fields: set[str] | None,
    exclude_fields: set[str],
) -> bool:
    return not any(
        (
            exclude_none and value is None,
            key.startswith("_"),
            key in META_FIELDS,
            key in exclude_fields,
            include_fields is not None and key not in include_fields,
        )
    )


def _should_sort_nested_hash_sequence(
    key: str,
    sort_nested_sequence_fields: set[str] | None,
) -> bool:
    return bool(
        sort_nested_sequence_fields is not None and key in sort_nested_sequence_fields
    )


def normalize_hash_identity_record(
    record: JsonDict,
    *,
    exclude_none: bool = False,
    include_fields: set[str] | None = None,
    exclude_fields: set[str] | None = None,
    sort_nested_sequence_fields: set[str] | None = None,
    datetime_policy: HashDatetimePolicy = "v1_date",
) -> JsonDict:
    """Normalize a record using the canonical hash-identity contract."""
    resolved_exclude_fields = exclude_fields or set()
    return {
        key: normalize_hash_identity_value(
            value,
            sort_nested_sequences=_should_sort_nested_hash_sequence(
                key,
                sort_nested_sequence_fields,
            ),
            datetime_policy=datetime_policy,
        )
        for key, value in record.items()
        if _should_include_hash_identity_field(
            key,
            value,
            exclude_none=exclude_none,
            include_fields=include_fields,
            exclude_fields=resolved_exclude_fields,
        )
    }


def serialize_hash_identity_canonical_json(
    data: JsonDict | Sequence[object],
) -> str:
    """Serialize normalized hash-identity material to canonical JSON bytes."""
    return serialize_json_canonical(data)
