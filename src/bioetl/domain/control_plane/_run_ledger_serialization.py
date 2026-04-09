"""Private serialization helpers for run-ledger payloads."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from bioetl.domain.normalization.control_plane import (
    normalize_control_plane_datetime,
    normalize_control_plane_uuid,
)


def normalize_ledger_value(value: object) -> object:
    """Normalize nested values into JSON-safe primitives."""
    if isinstance(value, dict):
        return normalize_ledger_mapping(value)
    collection_value = normalize_ledger_collection(value)
    if collection_value is not None:
        return collection_value
    return normalize_ledger_scalar(value)


def normalize_ledger_mapping(value: dict[object, object]) -> dict[str, object]:
    """Normalize dictionary values into deterministic JSON-safe primitives."""
    return {
        str(key): normalize_ledger_value(item)
        for key, item in sorted(value.items(), key=lambda item: str(item[0]))
    }


def normalize_ledger_collection(value: object) -> list[object] | None:
    """Normalize collection values while preserving deterministic ordering."""
    if isinstance(value, (list, tuple)):
        return [normalize_ledger_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        normalized = [normalize_ledger_value(item) for item in value]
        return sorted(normalized, key=lambda item: str(item))
    return None


def normalize_ledger_scalar(value: object) -> object:
    """Normalize scalar ledger values into JSON-safe primitives."""
    if isinstance(value, datetime):
        return normalize_control_plane_datetime(value)
    if isinstance(value, UUID):
        return normalize_control_plane_uuid(value)
    return value


def load_optional_str(payload: dict[str, object], key: str) -> str | None:
    """Extract an optional string field from a serialized mapping."""
    value = payload.get(key)
    return None if value is None else str(value)


def load_metrics_snapshot(raw_metrics: object) -> dict[str, int] | None:
    """Deserialize metrics snapshot payload safely."""
    if not isinstance(raw_metrics, dict):
        return None
    return {str(key): int(value) for key, value in raw_metrics.items()}


def load_details(raw_details: object) -> dict[str, object] | None:
    """Deserialize arbitrary details payload safely."""
    if not isinstance(raw_details, dict):
        return None
    return {str(key): value for key, value in raw_details.items()}
