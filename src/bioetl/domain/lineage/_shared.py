"""Shared serialization helpers for lineage models."""

from __future__ import annotations

from datetime import datetime

__all__ = [
    "load_attributes",
    "load_mapping",
    "load_optional_datetime",
    "load_optional_int",
    "load_optional_str",
    "load_optional_version",
    "normalize_mapping",
]


def normalize_mapping(values: dict[str, object]) -> dict[str, object]:
    """Return a detached shallow copy of attribute mappings."""
    return {str(key): value for key, value in values.items()}


def load_optional_str(payload: dict[str, object], key: str) -> str | None:
    """Return string field when present, otherwise None."""
    value = payload.get(key)
    return None if value is None else str(value)


def load_optional_datetime(payload: dict[str, object], key: str) -> datetime | None:
    """Return parsed datetime field when present, otherwise None."""
    value = payload.get(key)
    return None if value is None else datetime.fromisoformat(str(value))


def load_attributes(raw_attributes: object) -> dict[str, object]:
    """Return normalized attributes payload from serialized object."""
    if not isinstance(raw_attributes, dict):
        return {}
    return {str(key): value for key, value in raw_attributes.items()}


def load_mapping(raw_mapping: object) -> dict[str, object]:
    """Return normalized mapping payload from serialized object."""
    if not isinstance(raw_mapping, dict):
        return {}
    return {str(key): value for key, value in raw_mapping.items()}


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
