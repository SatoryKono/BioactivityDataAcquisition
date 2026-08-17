"""Shared serialization helpers for lineage models."""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import date, datetime
from enum import Enum
from pathlib import PurePath
from types import MappingProxyType
from uuid import UUID

from bioetl.domain.normalization._control_plane_primitives import (
    normalize_control_plane_datetime,
)
from bioetl.domain.normalization.json import serialize_json_canonical

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

_UNHANDLED = object()


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


def mapping_to_plain(values: Mapping[str, object]) -> dict[str, object]:
    """Return a JSON-safe deep plain-dict copy of a (possibly frozen) mapping."""
    return {str(key): _plain_value(value) for key, value in values.items()}


def _plain_set(value: set[object] | frozenset[object]) -> list[object]:
    # Deterministic order for set-valued attributes (JSON/export stability).
    plain_items = [_plain_value(item) for item in value]
    return sorted(plain_items, key=lambda item: serialize_json_canonical([item]))


def _plain_mapping(value: Mapping[object, object]) -> dict[str, object]:
    return {str(key): _plain_value(item) for key, item in value.items()}


def _plain_sequence(value: list[object] | tuple[object, ...]) -> list[object]:
    return [_plain_value(item) for item in value]


def _plain_value(value: object) -> object:
    container = _plain_container(value)
    if container is not _UNHANDLED:
        return container
    return _plain_leaf(value)


def _plain_container(value: object) -> object:
    """Return a recursively normalized container or the unhandled sentinel."""
    if isinstance(value, Mapping):
        return _plain_mapping(value)
    if isinstance(value, (list, tuple)):
        return _plain_sequence(value)
    if isinstance(value, (set, frozenset)):
        return _plain_set(value)
    return _UNHANDLED


def _plain_leaf(value: object) -> object:
    """Normalize one leaf to a JSON scalar, failing closed otherwise."""
    if isinstance(value, float):
        return _plain_float(value)
    if _is_json_scalar(value):
        return value
    temporal = _plain_temporal(value)
    if temporal is not _UNHANDLED:
        return temporal
    identifier = _plain_identifier(value)
    if identifier is not _UNHANDLED:
        return identifier
    raise TypeError(f"Lineage attributes require JSON-safe values; got {type(value).__name__}")


def _plain_float(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("Lineage attributes do not allow NaN or Infinity")
    return value


def _is_json_scalar(value: object) -> bool:
    return value is None or isinstance(value, (str, int, bool))


def _plain_temporal(value: object) -> object:
    if isinstance(value, datetime):
        return normalize_control_plane_datetime(value)
    if isinstance(value, date):
        return value.isoformat()
    return _UNHANDLED


def _plain_identifier(value: object) -> object:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, PurePath):
        return value.as_posix()
    if isinstance(value, Enum):
        return _plain_value(value.value)
    return _UNHANDLED


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
