"""Shared serialization helpers for lineage models."""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import date, datetime
from enum import Enum
from types import MappingProxyType
from uuid import UUID

from bioetl.domain.normalization._control_plane_primitives import (
    normalize_control_plane_datetime,
)

__all__ = [
    "load_attributes",
    "load_mapping",
    "load_optional_datetime",
    "load_optional_int",
    "load_optional_str",
    "load_optional_version",
    "mapping_to_plain",
    "normalize_mapping",
]



def _detach_mapping(value: Mapping[object, object]) -> MappingProxyType[str, object]:
    return MappingProxyType(
        {str(key): _detach_value(item) for key, item in value.items()}
    )


def _detach_set(value: set[object]) -> frozenset[object]:
    return frozenset(_detach_value(item) for item in value)


def _detach_sequence(value: list[object] | tuple[object, ...]) -> tuple[object, ...]:
    return tuple(_detach_value(item) for item in value)


def _detach_value(value: object) -> object:
    """Return a recursively detached, immutable view of *value* when mutable."""
    if isinstance(value, Mapping):
        return _detach_mapping(value)
    if isinstance(value, set):
        return _detach_set(value)
    if isinstance(value, (list, tuple)):
        return _detach_sequence(value)
    return value


def mapping_to_plain(value: object) -> object:
    """Return a recursively JSON-compatible copy of immutable attribute values."""
    if isinstance(value, Mapping):
        return {str(key): mapping_to_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [mapping_to_plain(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [mapping_to_plain(item) for item in sorted(value, key=repr)]
    return value


def normalize_mapping(values: Mapping[str, object]) -> Mapping[str, object]:
    """Return an immutable, recursively detached attribute mapping.

    Callers cannot mutate the result or share nested mutables with *values*.
    Keys are normalized to ``str`` for deterministic value-object storage.
    """
    return MappingProxyType(
        {str(key): _detach_value(value) for key, value in values.items()}
    )


def load_optional_str(payload: dict[str, object], key: str) -> str | None:
    """Return string field when present, otherwise None."""
    value = payload.get(key)
    return None if value is None else str(value)


def load_optional_datetime(payload: dict[str, object], key: str) -> datetime | None:
    """Return parsed datetime field when present, otherwise None."""
    value = payload.get(key)
    return None if value is None else datetime.fromisoformat(str(value))


def load_attributes(raw_attributes: object) -> Mapping[str, object]:
    """Return normalized attributes payload from serialized object."""
    if not isinstance(raw_attributes, dict):
        return MappingProxyType({})
    return normalize_mapping(raw_attributes)


def load_mapping(raw_mapping: object) -> Mapping[str, object]:
    """Return normalized mapping payload from serialized object."""
    if not isinstance(raw_mapping, dict):
        return MappingProxyType({})
    return normalize_mapping(raw_mapping)


def load_optional_version(
    payload: dict[str, object],
    key: str,
) -> int | str | None:
    """Return dataset version when present and representable."""
    value = payload.get(key)
    return value if isinstance(value, (int, str)) else None


def load_optional_int(payload: dict[str, object], key: str) -> int | None:
    """Return integer field when present, otherwise None."""
    value = payload.get(key)
    return None if value is None else int(str(value))
