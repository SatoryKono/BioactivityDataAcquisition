# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Shared snapshot-to-mapping serialization helpers for composition payloads."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from _typeshed import DataclassInstance


@runtime_checkable
class _ModelDumpHost(Protocol):
    def model_dump(
        self, *, mode: str = "python", exclude_none: bool = False
    ) -> dict[str, object]: ...


@runtime_checkable
class _DictHost(Protocol):
    def dict(self, *, exclude_none: bool = False) -> dict[str, object]: ...


__all__ = ["normalize_snapshot", "to_serializable_mapping"]


def _scalar_snapshot(value: object) -> tuple[bool, object]:
    """Normalize scalar snapshot values, reporting whether handled."""
    if isinstance(value, Enum):
        return True, value.value
    if isinstance(value, (UUID, Decimal, Path)):
        return True, str(value)
    if isinstance(value, datetime | date | time):
        return True, value.isoformat()
    if isinstance(value, timedelta):
        return True, value.total_seconds()
    return False, value


def _is_plain_sequence(value: object) -> bool:
    """Return True for non-text sequences that normalize element-wise."""
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    )


def _iterable_snapshot(value: object) -> tuple[bool, object]:
    """Normalize sequence/set snapshot values, reporting whether handled."""
    if _is_plain_sequence(value) or isinstance(value, (set, frozenset)):
        items = cast("Iterable[object]", value)
        return True, [normalize_snapshot(item) for item in items]
    return False, value


def _compound_snapshot(value: object) -> tuple[bool, object]:
    """Normalize dataclass/mapping snapshot values, reporting whether handled."""
    if not isinstance(value, type) and is_dataclass(value):
        return True, normalize_snapshot(asdict(cast("DataclassInstance", value)))
    if isinstance(value, Mapping):
        return True, {
            str(key): normalize_snapshot(item) for key, item in value.items()
        }
    return _iterable_snapshot(value)


def _object_snapshot(value: object) -> tuple[bool, object]:
    """Normalize public-attribute objects, reporting whether handled."""
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return True, normalize_snapshot(
            {key: item for key, item in vars(value).items() if not key.startswith("_")}
        )
    return False, value


def normalize_snapshot(value: object) -> object:
    """Normalize snapshot values into JSON-serializable primitives."""
    for step in (_scalar_snapshot, _compound_snapshot, _object_snapshot):
        handled, result = step(value)
        if handled:
            return result
    return value


def _public_dict_payload(value: object) -> tuple[bool, object]:
    """Extract the public-attribute payload, reporting whether handled."""
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return True, {
            key: item for key, item in vars(value).items() if not key.startswith("_")
        }
    return False, value


def _snapshot_payload(value: object) -> object:
    """Extract the raw payload for manifest mapping serialization."""
    if isinstance(value, _ModelDumpHost):
        return value.model_dump(mode="python", exclude_none=True)
    if isinstance(value, _DictHost):
        return value.dict(exclude_none=True)
    handled, payload = _public_dict_payload(value)
    if handled:
        return payload
    return normalize_snapshot(value)


def to_serializable_mapping(value: object) -> dict[str, object]:
    """Return a normalized mapping for manifest payload serialization."""
    payload = _snapshot_payload(value)
    if not isinstance(payload, dict):
        return {"value": normalize_snapshot(payload)}
    normalized = normalize_snapshot(payload)
    if not isinstance(normalized, dict):
        raise TypeError("Manifest snapshot normalization must return a mapping")
    return normalized
