"""Validate event durations and immutable metadata snapshots."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from math import isfinite
from uuid import UUID

from bioetl.domain.immutability import FrozenDict, FrozenList


def validate_metadata_snapshot(value: object) -> None:
    """Accept immutable identity scalars and recursively snapshottable containers."""
    if isinstance(value, (dict, FrozenDict)):
        _validate_metadata_mapping(value)
        return
    if isinstance(value, (list, tuple, FrozenList)):
        for nested in value:
            validate_metadata_snapshot(nested)
        return
    _validate_metadata_scalar(value)


def _validate_metadata_mapping(value: dict[str, object] | FrozenDict) -> None:
    for key, nested in value.items():
        if not isinstance(key, str):
            raise TypeError("Event metadata mappings require string keys")
        validate_metadata_snapshot(nested)


def _validate_metadata_scalar(value: object) -> None:
    _validate_metadata_float(value)
    if isinstance(value, Enum):
        _validate_metadata_scalar(value.value)
        return
    if value is None or isinstance(value, (str, int, float, datetime, UUID)):
        return
    raise TypeError(f"Unsupported event metadata value: {type(value).__name__}")


def _validate_metadata_float(value: object) -> None:
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("Event metadata does not allow NaN or Infinity")


def validate_duration(seconds: float) -> None:
    """Require a finite, non-negative elapsed duration."""
    if not isfinite(seconds):
        raise ValueError(f"duration_seconds must be finite: {seconds}")
    if seconds < 0.0:
        raise ValueError(f"duration_seconds cannot be negative: {seconds}")
