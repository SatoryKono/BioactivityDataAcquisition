"""Private normalization helpers for run-manifest payloads."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import NoReturn, cast
from uuid import UUID

from bioetl.domain.normalization.control_plane import (
    normalize_control_plane_datetime,
    normalize_control_plane_uuid,
)


class _FrozenManifestMapping(dict[object, object]):
    """Immutable dict-compatible payload mapping for manifest snapshots."""

    __slots__ = ()

    @staticmethod
    def _raise_immutable() -> NoReturn:
        raise TypeError("RunManifest payload mappings are immutable")

    def __setitem__(self, key: object, value: object) -> None:
        self._raise_immutable()

    def __delitem__(self, key: object) -> None:
        self._raise_immutable()

    def clear(self) -> None:
        self._raise_immutable()

    def pop(self, _key: object, _default: object = None) -> object:
        self._raise_immutable()

    def popitem(self) -> tuple[object, object]:
        self._raise_immutable()

    def setdefault(self, _key: object, _default: object = None) -> object:
        self._raise_immutable()

    def update(self, *_args: object, **_kwargs: object) -> None:
        self._raise_immutable()

    def __ior__(self, other: object) -> NoReturn:
        self._raise_immutable()


def freeze_manifest_payload(value: object) -> object:
    """Deep-freeze manifest payload values while preserving dict-like access."""
    for freeze_value in _MANIFEST_PAYLOAD_FREEZERS:
        frozen_value = freeze_value(value)
        if frozen_value is not None:
            return frozen_value
    return deepcopy(value)


def _freeze_manifest_mapping(
    value: object,
) -> _FrozenManifestMapping | None:
    """Deep-freeze mapping values when present."""
    if not isinstance(value, Mapping):
        return None
    return _FrozenManifestMapping(
        (deepcopy(key), freeze_manifest_payload(item)) for key, item in value.items()
    )


def _freeze_manifest_sequence(value: object) -> tuple[object, ...] | None:
    """Deep-freeze ordered collection values when present."""
    if not isinstance(value, (list, tuple)):
        return None
    return tuple(freeze_manifest_payload(item) for item in value)


def _freeze_manifest_set_like(value: object) -> frozenset[object] | None:
    """Deep-freeze set-like values when present."""
    if not isinstance(value, (set, frozenset)):
        return None
    return frozenset(freeze_manifest_payload(item) for item in value)


_MANIFEST_PAYLOAD_FREEZERS: tuple[Callable[[object], object | None], ...] = (
    _freeze_manifest_mapping,
    _freeze_manifest_sequence,
    _freeze_manifest_set_like,
)


def normalize_manifest_serializable(value: object) -> object:
    """Normalize nested values into JSON-serializable primitives."""
    dataclass_value = _normalize_manifest_dataclass(value)
    if dataclass_value is not None:
        return dataclass_value
    collection_value = _normalize_manifest_collection(value)
    if collection_value is not None:
        return collection_value
    return _normalize_manifest_scalar(value)


def normalize_manifest_created_at(value: datetime) -> datetime:
    """Canonicalize manifest timestamps to UTC-aware datetimes."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_manifest_mapping(value: Mapping[object, object]) -> dict[str, object]:
    """Normalize nested mappings into deterministic JSON-serializable values."""
    return {
        str(key): normalize_manifest_serializable(item)
        for key, item in sorted(value.items(), key=lambda item: str(item[0]))
    }


def _normalize_manifest_scalar(value: object) -> object:
    """Normalize scalar values into JSON-serializable primitives."""
    if isinstance(value, datetime):
        return normalize_control_plane_datetime(value)
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, UUID):
        return normalize_control_plane_uuid(value)
    return value


def _normalize_manifest_dataclass(value: object) -> dict[str, object] | None:
    """Normalize dataclass instances when present."""
    if not is_dataclass(value) or isinstance(value, type):
        return None
    return _normalize_manifest_mapping(cast("Mapping[object, object]", asdict(value)))


def _normalize_manifest_collection(value: object) -> object | None:
    """Normalize collection-like values into JSON-friendly shapes."""
    if isinstance(value, dict):
        return _normalize_manifest_mapping(value)
    sequence_value = _normalize_manifest_sequence(value)
    if sequence_value is not None:
        return sequence_value
    return _normalize_manifest_set_like(value)


def _normalize_manifest_sequence(value: object) -> list[object] | None:
    """Normalize ordered collection values when present."""
    if not isinstance(value, (list, tuple)):
        return None
    return [normalize_manifest_serializable(item) for item in value]


def _normalize_manifest_set_like(value: object) -> list[object] | None:
    """Normalize set-like values into deterministically sorted lists."""
    if not isinstance(value, (set, frozenset)):
        return None
    normalized = [normalize_manifest_serializable(item) for item in value]
    return sorted(normalized, key=lambda item: str(item))
