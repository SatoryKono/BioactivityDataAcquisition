"""Shared primitive canonicalization helpers for control-plane payloads."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime
from enum import Enum
from typing import TypeAlias, cast
from uuid import UUID

from bioetl.domain.normalization.json import (
    deserialize_json_value,
    serialize_json_canonical,
)

_MAPPING_STR_OBJECT: TypeAlias = Mapping[str, object]


def normalize_control_plane_uuid(value: UUID | str) -> str:
    """Return one canonical UUID string representation."""
    if isinstance(value, UUID):
        return str(value)
    return str(UUID(str(value).strip()))


def normalize_control_plane_datetime(value: datetime) -> str:
    """Return canonical UTC ISO-8601 representation with ``Z`` suffix."""
    normalized = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    return normalized.astimezone(UTC).isoformat().replace("+00:00", "Z")


def normalize_optional_datetime(value: object | None) -> str | None:
    """Normalize optional datetime-compatible values."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return normalize_control_plane_datetime(value)
    if isinstance(value, str):
        return normalize_control_plane_datetime(datetime.fromisoformat(value))
    raise TypeError(f"Expected datetime-compatible value, got {type(value).__name__}")


def normalize_optional_uuid(value: object | None) -> str | None:
    """Normalize optional UUID-compatible values."""
    if value is None:
        return None
    if isinstance(value, (UUID, str)):
        return normalize_control_plane_uuid(value)
    raise TypeError(f"Expected UUID-compatible value, got {type(value).__name__}")


def canonicalize_container(
    value: dict[str, object] | list[object],
) -> dict[str, object] | list[object]:
    """Round-trip a container through canonical JSON for stable ordering."""
    serialized = serialize_json_canonical(value)
    return cast("dict[str, object] | list[object]", deserialize_json_value(serialized))


def _canonical_sort_key(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _normalize_dataclass(value: object) -> dict[str, object] | None:
    if not is_dataclass(value) or isinstance(value, type):
        return None
    return normalize_mapping(cast(_MAPPING_STR_OBJECT, asdict(value)))


def _normalize_scalar(value: object) -> object:
    if isinstance(value, datetime):
        return normalize_control_plane_datetime(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return normalize_control_plane_uuid(value)
    if isinstance(value, Enum):
        return _normalize_scalar(value.value)
    return value


def normalize_set_like_sequence(values: Iterable[object]) -> list[object]:
    """Normalize an iterable as a set-like, deterministically sorted sequence."""
    normalized = [normalize_canonical_object(item) for item in values]
    return sorted(normalized, key=_canonical_sort_key)


def _normalize_sequence(values: Sequence[object]) -> list[object]:
    normalized = [normalize_canonical_object(item) for item in values]
    return cast("list[object]", canonicalize_container(normalized))


def normalize_mapping(value: Mapping[str, object]) -> dict[str, object]:
    """Normalize a mapping into canonical JSON-safe primitives."""
    normalized = {
        str(key): normalize_canonical_object(item)
        for key, item in sorted(value.items(), key=lambda item: str(item[0]))
    }
    return cast("dict[str, object]", canonicalize_container(normalized))


def normalize_canonical_object(value: object) -> object:
    """Normalize a nested control-plane value recursively."""
    dataclass_value = _normalize_dataclass(value)
    if dataclass_value is not None:
        return dataclass_value
    if isinstance(value, Mapping):
        return normalize_mapping(cast(_MAPPING_STR_OBJECT, value))
    if isinstance(value, (list, tuple)):
        return _normalize_sequence(value)
    if isinstance(value, (set, frozenset)):
        normalized = normalize_set_like_sequence(value)
        return cast("list[object]", canonicalize_container(normalized))
    return _normalize_scalar(value)


def normalize_metric_count(value: object) -> int:
    """Normalize one metric snapshot value to a stable integer."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"Unsupported metric snapshot value: {type(value).__name__}")


def normalize_run_ledger_metrics_snapshot(
    value: object | None,
) -> dict[str, int] | None:
    """Normalize metrics snapshots into sorted integer mappings."""
    if not isinstance(value, Mapping):
        return None
    return {
        str(key): normalize_metric_count(item)
        for key, item in sorted(value.items(), key=lambda item: str(item[0]))
    }


def normalize_run_ledger_details(value: object | None) -> dict[str, object] | None:
    """Normalize nested diagnostic details when the payload provides them."""
    if not isinstance(value, Mapping):
        return None
    return normalize_mapping(cast(_MAPPING_STR_OBJECT, value))
