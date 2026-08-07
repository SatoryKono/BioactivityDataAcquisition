"""Shared serialization helpers for lineage models."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from types import MappingProxyType

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


def _detach_value(value: object) -> object:
    """Return a recursively detached, immutable view of *value* when mutable."""
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _detach_value(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_detach_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_detach_value(item) for item in value)
    if isinstance(value, set):
        return frozenset(_detach_value(item) for item in value)
    return value



def mapping_to_plain(values: Mapping[str, object]) -> dict[str, object]:
    """Return a JSON-safe deep plain-dict copy of a (possibly frozen) mapping."""
    return {str(key): _plain_value(value) for key, value in values.items()}


def _plain_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_plain_value(item) for item in value]
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
