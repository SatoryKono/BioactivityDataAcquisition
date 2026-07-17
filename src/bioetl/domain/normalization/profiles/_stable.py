"""Stable value normalization utilities for deterministic hashing.

Extracted from base.py to reduce file size and improve separation of concerns.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping


def _sha256_hex(payload: object) -> str:
    """Return canonical SHA256 hex digest for one JSON-serializable payload."""
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _stable_mapping(value: Mapping) -> dict[str, object]:
    """Normalize mapping with sorted keys."""
    return {
        str(k): _stable_value(v)
        for k, v in sorted(value.items(), key=lambda i: str(i[0]))
    }


def _stable_sequence(value: list[object] | tuple[object, ...]) -> list[object]:
    """Normalize sequence recursively."""
    return [_stable_value(v) for v in value]


def _stable_set(value: set[object] | frozenset[object]) -> list[object]:
    """Normalize set to sorted list."""
    normalized = [_stable_value(item) for item in value]
    return sorted(
        normalized,
        key=lambda item: json.dumps(item, sort_keys=True, default=str),
    )


def _stable_callable(value: object) -> dict[str, object]:
    """Normalize callable to module/qualname reference."""
    return {
        "module": getattr(value, "__module__", type(value).__module__),
        "qualname": getattr(value, "__qualname__", type(value).__qualname__),
    }


def _is_primitive(value: object) -> bool:
    """Check if value is a primitive JSON type."""
    return isinstance(value, (str, int, float, bool)) or value is None


def _stable_value(value: object) -> object:
    """Normalize value to stable representation for deterministic hashing."""
    type_handlers = {
        Mapping: _stable_mapping,
        list: _stable_sequence,
        tuple: _stable_sequence,
        set: _stable_set,
        frozenset: _stable_set,
        bytes: lambda v: v.hex(),
    }
    for type_check, handler in type_handlers.items():
        if isinstance(value, type_check):
            return handler(value)
    if callable(value):
        return _stable_callable(value)
    if _is_primitive(value):
        return value
    return repr(value)
