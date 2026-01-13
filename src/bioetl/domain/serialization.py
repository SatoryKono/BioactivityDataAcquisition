"""Centralized JSON serialization for deterministic content hashing.

Provides canonical JSON serialization using orjson for optimal performance.
All serialization operations use sorted keys and compact output for
deterministic results per RULES.md §2.8.1.

Requirements:
- REQ-ARCH-030: Deterministic writes for reproducibility
- REQ-ID-001 to REQ-ID-008: Content hash algorithm

This module provides a functional API that wraps the JsonEncoderPort
implementations. It automatically selects orjson when available for
2-10x performance improvement.

Usage:
    >>> from bioetl.domain.serialization import serialize_to_json, deserialize_from_json
    >>> data = {"b": 2, "a": 1}
    >>> serialize_to_json(data)
    '{"a":1,"b":2}'  # Sorted keys, compact
    >>> deserialize_from_json('{"a": 1}')
    {'a': 1}
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

# Try importing orjson for high-performance JSON serialization
try:
    import orjson

    _ORJSON_AVAILABLE = True
except ImportError:
    orjson = None  # type: ignore[assignment]
    _ORJSON_AVAILABLE = False


def serialize_to_json(
    data: dict[str, Any] | list[Any],
    *,
    sort_keys: bool = True,
    ensure_ascii: bool = True,
) -> str:
    """Serialize data to canonical JSON string for content hashing.

    Uses orjson when available for optimal performance (2-10x faster
    than stdlib json). Falls back to stdlib json when orjson is not
    installed.

    The output is deterministic (sorted keys, compact separators) to
    ensure consistent content hashes across runs per RULES.md §2.8.1.

    Args:
        data: Dictionary or list to serialize.
        sort_keys: If True, output keys in sorted order (default: True).
        ensure_ascii: If True, escape non-ASCII characters (default: True).
            Set to True for canonical output used in content hashing.

    Returns:
        Compact JSON string with sorted keys.

    Example:
        >>> serialize_to_json({"b": 2, "a": 1})
        '{"a":1,"b":2}'
        >>> serialize_to_json({"key": "value"}, ensure_ascii=False)
        '{"key":"value"}'

    """
    if _ORJSON_AVAILABLE:
        return _serialize_with_orjson(
            data, sort_keys=sort_keys, ensure_ascii=ensure_ascii
        )
    return _serialize_with_stdlib(data, sort_keys=sort_keys, ensure_ascii=ensure_ascii)


def serialize_to_json_canonical(data: dict[str, Any]) -> str:
    """Serialize data to canonical JSON for content hash computation.

    This is a convenience wrapper that always uses:
    - Sorted keys
    - Compact separators
    - ASCII-only output

    This matches the canonical JSON format specified in RULES.md §2.8.1
    for computing content hashes.

    Args:
        data: Dictionary to serialize.

    Returns:
        Canonical JSON string suitable for hashing.

    Example:
        >>> serialize_to_json_canonical({"b": 2, "a": 1})
        '{"a":1,"b":2}'

    """
    return serialize_to_json(data, sort_keys=True, ensure_ascii=True)


def deserialize_from_json(data: str | bytes) -> dict[str, Any] | list[Any]:
    """Deserialize JSON string or bytes to Python object.

    Uses orjson when available for optimal performance.
    Falls back to stdlib json when orjson is not installed.

    Args:
        data: JSON string or bytes to deserialize.

    Returns:
        Deserialized Python object (dict or list).

    Raises:
        ValueError: If JSON is invalid.

    Example:
        >>> deserialize_from_json('{"a": 1}')
        {'a': 1}
        >>> deserialize_from_json(b'[1, 2, 3]')
        [1, 2, 3]

    """
    if _ORJSON_AVAILABLE:
        return _deserialize_with_orjson(data)
    return _deserialize_with_stdlib(data)


def _escape_non_ascii(text: str) -> str:
    """Escape non-ASCII characters using JSON unicode escape format (\\uXXXX)."""
    return "".join(f"\\u{ord(c):04x}" if ord(c) > 127 else c for c in text)


def _has_non_ascii(text: str) -> bool:
    """Check if text contains non-ASCII characters."""
    return any(ord(c) > 127 for c in text)


def _get_orjson_options(sort_keys: bool) -> int:
    """Get orjson options based on configuration."""
    assert orjson is not None
    options = orjson.OPT_SERIALIZE_NUMPY
    return options | orjson.OPT_SORT_KEYS if sort_keys else options


def _serialize_with_orjson(
    data: dict[str, Any] | list[Any],
    *,
    sort_keys: bool = True,
    ensure_ascii: bool = True,
) -> str:
    """Serialize using orjson with OPT_SORT_KEYS for determinism."""
    assert orjson is not None
    result = orjson.dumps(data, option=_get_orjson_options(sort_keys)).decode("utf-8")
    # orjson doesn't have ensure_ascii option - escape non-ASCII if needed
    return (
        _escape_non_ascii(result) if ensure_ascii and _has_non_ascii(result) else result
    )


def _serialize_with_stdlib(
    data: dict[str, Any] | list[Any],
    *,
    sort_keys: bool = True,
    ensure_ascii: bool = True,
) -> str:
    """Serialize using stdlib json as fallback."""
    import json

    return json.dumps(
        data,
        sort_keys=sort_keys,
        separators=(",", ":"),
        ensure_ascii=ensure_ascii,
    )


def _deserialize_with_orjson(data: str | bytes) -> dict[str, Any] | list[Any]:
    """Deserialize using orjson."""
    assert orjson is not None
    try:
        result: dict[str, Any] | list[Any] = orjson.loads(data)
        return result
    except orjson.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e


def _deserialize_with_stdlib(data: str | bytes) -> dict[str, Any] | list[Any]:
    """Deserialize using stdlib json as fallback."""
    import json

    try:
        result: dict[str, Any] | list[Any] = json.loads(data)
        return result
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e


@lru_cache(maxsize=1)
def is_orjson_available() -> bool:
    """Check if orjson is available for high-performance serialization.

    Returns:
        True if orjson is installed, False otherwise.

    """
    return _ORJSON_AVAILABLE


__all__ = [
    "deserialize_from_json",
    "is_orjson_available",
    "serialize_to_json",
    "serialize_to_json_canonical",
]
