# basedpyright residual burn-down (shrink-only product surface).
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
from bioetl.domain.types import JsonDict
    >>> data = {"b": 2, "a": 1}
    >>> serialize_to_json(data)
    '{"a":1,"b":2}'  # Sorted keys, compact
    >>> deserialize_from_json('{"a": 1}')
    {'a': 1}
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import TYPE_CHECKING, TypeGuard

from bioetl.domain.normalization.json import (
    canonicalize_json_string as _canonicalize_json_string,
)
from bioetl.domain.normalization.json import (
    deserialize_json_value as _deserialize_json_value,
)
from bioetl.domain.normalization.json import (
    serialize_json_canonical as _serialize_json_canonical,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    import pyarrow as pa

# Try importing orjson for high-performance JSON serialization
try:
    import orjson

    _orjson_available = True
except ImportError:
    orjson = None  # type: ignore[assignment]
    _orjson_available = False


def serialize_to_json(
    data: JsonDict | Sequence[object],  # Any: JSON arrays contain heterogeneous values
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
    _reject_non_finite_json_floats(data)
    if _orjson_available:
        return _serialize_with_orjson(
            data, sort_keys=sort_keys, ensure_ascii=ensure_ascii
        )
    return _serialize_with_stdlib(data, sort_keys=sort_keys, ensure_ascii=ensure_ascii)


def serialize_to_json_canonical(
    data: JsonDict,  # Any: JSON values are heterogeneous
) -> str:  # Any: JSON values are heterogeneous
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
    return _serialize_json_canonical(data)


def serialize_to_canonical_json(
    obj: JsonDict,  # Any: JSON values are heterogeneous
) -> str:
    """Serialize a mapping to canonical JSON via the domain hashing contract.

    This alias preserves the existing dict-oriented public contract used by
    content hashing helpers while exposing a clearer public entrypoint name.

    Args:
        obj: Dictionary to serialize.

    Returns:
        Canonical JSON string suitable for deterministic hashing.
    """
    return serialize_to_json_canonical(obj)


_NON_ASCII_RE = re.compile(r"[^\x00-\x7F]")


def deserialize_from_json(
    data: str | bytes,
) -> JsonDict | list[object]:  # Any: JSON deserialization produces heterogeneous types
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
    return _deserialize_json_value(data)


def canonicalize_json_string(value: str | None) -> str | None:
    """Normalize JSON string to canonical deterministic JSON representation."""
    return _canonicalize_json_string(value)


def _escape_non_ascii(text: str) -> str:
    """Escape non-ASCII characters using JSON unicode escape format.

    Supplementary-plane characters become UTF-16 surrogate pairs.
    """
    return _NON_ASCII_RE.sub(_escape_unicode_match, text)


def _escape_unicode_match(match: re.Match[str]) -> str:
    """Return a valid JSON escape, including surrogate pairs outside the BMP."""
    code_point = ord(match.group(0))
    if code_point <= 0xFFFF:
        return f"\\u{code_point:04x}"
    supplementary = code_point - 0x10000
    high_surrogate = 0xD800 + (supplementary >> 10)
    low_surrogate = 0xDC00 + (supplementary & 0x3FF)
    return f"\\u{high_surrogate:04x}\\u{low_surrogate:04x}"


def _reject_non_finite_json_floats(value: object) -> None:
    """Reject NaN/Inf so orjson and stdlib cannot diverge on non-finite floats."""
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("JSON serialization does not allow NaN or Infinity")
    _reject_nested_non_finite_json_floats(value)


def _reject_nested_non_finite_json_floats(value: object) -> None:
    if isinstance(value, Mapping):
        for nested in value.values():
            _reject_non_finite_json_floats(nested)
        return
    if _is_json_like_sequence(value):
        for nested in value:
            _reject_non_finite_json_floats(nested)


def _is_json_like_sequence(value: object) -> TypeGuard[Sequence[object]]:
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    )


def _has_non_ascii(text: str) -> bool:
    """Check if text contains non-ASCII characters.

    Performance note: `str.isascii()` is a C-optimized built-in method that is
    orders of magnitude (~300x) faster than manual iteration.
    """
    return not text.isascii()


def _get_orjson_options(sort_keys: bool) -> int:
    """Get orjson options based on configuration."""
    assert orjson is not None
    options: int = orjson.OPT_SERIALIZE_NUMPY
    result: int = options | orjson.OPT_SORT_KEYS if sort_keys else options
    return result


def _serialize_with_orjson(
    data: JsonDict | Sequence[object],  # Any: JSON arrays contain heterogeneous values
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
    data: JsonDict | Sequence[object],  # Any: JSON arrays contain heterogeneous values
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
        allow_nan=False,
    )


@lru_cache(maxsize=1)
def is_orjson_available() -> bool:
    """Check if orjson is available for high-performance serialization.

    Returns:
        True if orjson is installed, False otherwise.

    """
    return _orjson_available


def flatten_arrow_table_for_export(table: pa.Table) -> pa.Table:
    """Convert list/struct Arrow columns to JSON strings for export-safe flattening.

    Args:
        table: PyArrow Table potentially containing list, large_list, or struct columns.

    Returns:
        PyArrow Table with complex columns serialized as JSON strings.
    """
    from bioetl.domain.serialization_arrow import flatten_arrow_table

    return flatten_arrow_table(table)


__all__ = [
    "canonicalize_json_string",
    "deserialize_from_json",
    "flatten_arrow_table_for_export",
    "is_orjson_available",
    "serialize_to_canonical_json",
    "serialize_to_json",
    "serialize_to_json_canonical",
]
