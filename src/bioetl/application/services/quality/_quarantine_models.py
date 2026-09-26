"""Shared models for quarantine admin services and mixins."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import cast

from bioetl.domain.types import JsonDict


def _freeze_json_like(value: object) -> object:
    """Recursively freeze JSON-like payloads into read-only views."""
    if isinstance(value, Mapping):
        frozen_mapping = {
            str(key): _freeze_json_like(nested_value)
            for key, nested_value in value.items()
        }
        return MappingProxyType(frozen_mapping)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_freeze_json_like(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    """Representation of a quarantined record."""

    error_code: str | None
    payload: JsonDict
    batch_id: str | None
    pipeline: str
    ingestion_ts: datetime | None
    metadata: JsonDict

    def __post_init__(self) -> None:
        """Freeze nested payload and metadata containers at the boundary."""
        object.__setattr__(
            self,
            "payload",
            cast("JsonDict", _freeze_json_like(self.payload)),
        )
        object.__setattr__(
            self,
            "metadata",
            cast("JsonDict", _freeze_json_like(self.metadata)),
        )


__all__ = ["QuarantineRecord"]
