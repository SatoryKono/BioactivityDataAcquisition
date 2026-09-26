"""Shared application settings validation helpers."""

from __future__ import annotations

__all__ = ["coerce_silver_dedup_timeout_seconds"]


def coerce_silver_dedup_timeout_seconds(value: object) -> float:
    """Coerce empty, bool, and non-positive timeout values to the safe default."""
    if value is None or value == "":
        return 60.0
    if isinstance(value, bool):
        return 60.0
    if isinstance(value, (int, float, str)):
        parsed = float(value)
        return parsed if parsed > 0 else 60.0
    return 60.0
