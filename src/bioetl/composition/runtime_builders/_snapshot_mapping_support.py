# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Shared snapshot-to-mapping serialization helpers for runtime builders."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

__all__ = ["normalize_snapshot", "to_serializable_mapping"]


@runtime_checkable
class _ModelDumpHost(Protocol):
    def model_dump(
        self, *, mode: str = "python", exclude_none: bool = False
    ) -> Mapping[str, object]: ...


@runtime_checkable
class _DictHost(Protocol):
    def dict(self, *, exclude_none: bool = False) -> Mapping[str, object]: ...


def normalize_snapshot(value: object) -> object:
    """Normalize snapshot values into JSON-serializable primitives."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if not isinstance(value, type) and is_dataclass(value):
        return normalize_snapshot(asdict(cast("DataclassInstance", value)))
    if isinstance(value, dict):
        return {str(key): normalize_snapshot(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [normalize_snapshot(item) for item in value]
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return normalize_snapshot(
            {key: item for key, item in vars(value).items() if not key.startswith("_")}
        )
    return value


def to_serializable_mapping(value: object) -> dict[str, object]:
    """Return a normalized mapping for manifest payload serialization."""
    if isinstance(value, _ModelDumpHost):
        payload: object = value.model_dump(mode="json", exclude_none=True)
    elif isinstance(value, _DictHost):
        payload = value.dict(exclude_none=True)
    elif hasattr(value, "__dict__") and not isinstance(value, type):
        payload = {
            key: item for key, item in vars(value).items() if not key.startswith("_")
        }
    else:
        payload = normalize_snapshot(value)
    if not isinstance(payload, dict):
        return {"value": normalize_snapshot(payload)}
    normalized = normalize_snapshot(payload)
    if not isinstance(normalized, dict):
        raise TypeError("Manifest snapshot normalization must return a mapping")
    return normalized
