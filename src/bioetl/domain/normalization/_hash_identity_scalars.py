"""Scalar normalization helpers for hash-identity material."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime
from functools import singledispatch
from typing import Literal

HashDatetimePolicy = Literal["v1_date", "v2_datetime_utc"]

__all__ = ["HashDatetimePolicy", "normalize_hash_scalar_for_policy"]


@singledispatch
def _normalize_scalar(value: object) -> object:
    """Normalize one scalar value for the hash-identity contract."""
    return value


@_normalize_scalar.register(float)
def _normalize_float(value: float) -> float | None:
    """Normalize floats for deterministic hashing and dedup identity."""
    if math.isnan(value) or math.isinf(value):
        return None
    rounded = round(value, 10)
    if abs(rounded) <= 1e-15:
        return 0.0
    return rounded


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


def normalize_hash_scalar_for_policy(
    value: object,
    *,
    datetime_policy: HashDatetimePolicy,
) -> object:
    """Normalize one scalar under the selected versioned hash policy."""
    if isinstance(value, datetime) and datetime_policy == "v2_datetime_utc":
        return _normalize_datetime_utc(value)
    return _normalize_scalar(value)
