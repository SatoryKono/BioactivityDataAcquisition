"""JSON normalization helpers for run-manifest inspection."""

from __future__ import annotations

import json
from datetime import date, datetime
from uuid import UUID


def normalize_typed_jsonable(value: object) -> object | None:
    """Normalize datetime/date/UUID/bytes values; return None for other types."""
    if isinstance(value, datetime):
        return {
            "__type__": "datetime",
            "isoformat": value.isoformat(),
            "aware": value.tzinfo is not None,
            "tz": None if value.tzinfo is None else str(value.tzinfo),
        }
    if isinstance(value, date):
        return {"__type__": "date", "isoformat": value.isoformat()}
    if isinstance(value, UUID):
        return {"__type__": "uuid", "value": str(value)}
    if isinstance(value, bytes):
        return {"__type__": "bytes", "hex": value.hex()}
    return None


def normalize_jsonable(value: object) -> object:
    """Normalize supported values without collapsing distinct types."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    typed = normalize_typed_jsonable(value)
    if typed is not None:
        return typed
    if isinstance(value, dict):
        return {str(key): normalize_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [normalize_jsonable(item) for item in value]
    if isinstance(value, set | frozenset):
        return sorted(
            (normalize_jsonable(item) for item in value),
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
        )
    return {
        "__type__": "unsupported",
        "qualname": type(value).__qualname__,
        "repr": repr(value),
    }
