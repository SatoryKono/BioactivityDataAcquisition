# basedpyright residual burn-down (shrink-only product surface).
"""Pure canonical JSON normalization helpers."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from bioetl.domain.types import JsonDict
else:
    JsonDict = dict[str, object]

try:
    import orjson

    _orjson_available = True
except ImportError:
    orjson = None  # type: ignore[assignment]
    _orjson_available = False

__all__ = [
    "canonicalize_json_string",
    "deserialize_json_value",
    "serialize_json_canonical",
]

_NON_ASCII_RE = re.compile(r"[^\x00-\x7F]")


def _escape_non_ascii(text: str) -> str:
    """Escape non-ASCII characters using JSON unicode escape format."""
    return _NON_ASCII_RE.sub(lambda m: f"\\u{ord(m.group(0)):04x}", text)


def _has_non_ascii(text: str) -> bool:
    """Check if text contains non-ASCII characters."""
    return not text.isascii()


def _get_orjson_options(sort_keys: bool) -> int:
    """Get orjson options based on configuration."""
    assert orjson is not None
    options: int = orjson.OPT_SERIALIZE_NUMPY
    result: int = options | orjson.OPT_SORT_KEYS if sort_keys else options
    return result


def _serialize_with_orjson(
    data: JsonDict | Sequence[object],
    *,
    sort_keys: bool = True,
    ensure_ascii: bool = True,
) -> str:
    """Serialize using orjson with optional ASCII escaping."""
    assert orjson is not None
    result = orjson.dumps(data, option=_get_orjson_options(sort_keys)).decode("utf-8")
    return (
        _escape_non_ascii(result) if ensure_ascii and _has_non_ascii(result) else result
    )


def _serialize_with_stdlib(
    data: JsonDict | Sequence[object],
    *,
    sort_keys: bool = True,
    ensure_ascii: bool = True,
) -> str:
    """Serialize using stdlib json as fallback."""
    return json.dumps(
        data,
        sort_keys=sort_keys,
        separators=(",", ":"),
        ensure_ascii=ensure_ascii,
        allow_nan=False,
    )


def _assert_no_non_finite_floats(value: object) -> None:
    """Reject NaN/Infinity to keep canonical JSON stable across runtimes."""
    if isinstance(value, float):
        _assert_finite_float(value)
        return
    for nested_value in _iter_nested_json_values(value):
        _assert_no_non_finite_floats(nested_value)


def _assert_finite_float(value: float) -> None:
    """Reject one non-finite float value."""
    if math.isfinite(value):
        return
    raise ValueError("Canonical JSON serialization does not allow NaN or Infinity")


def _iter_nested_json_values(value: object) -> Sequence[object]:
    """Return nested JSON-like values that need recursive inspection."""
    if isinstance(value, dict):
        return list(value.values())
    if _is_nested_json_sequence(value):
        return cast(Sequence[object], value)
    return ()


def _is_nested_json_sequence(value: object) -> bool:
    """Return whether the value is a JSON-like sequence."""
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    )


def serialize_json_canonical(data: JsonDict | Sequence[object]) -> str:
    """Serialize data to deterministic canonical JSON string."""
    _assert_no_non_finite_floats(data)
    if _orjson_available:
        return _serialize_with_orjson(data, sort_keys=True, ensure_ascii=True)
    return _serialize_with_stdlib(data, sort_keys=True, ensure_ascii=True)


def deserialize_json_value(data: str | bytes) -> JsonDict | list[object]:
    """Deserialize JSON string or bytes to Python object."""
    if _orjson_available:
        assert orjson is not None
        try:
            parsed_value = cast("JsonDict | list[object]", orjson.loads(data))
            return parsed_value
        except orjson.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc}") from exc
    try:
        parsed_value = cast("JsonDict | list[object]", json.loads(data))
        return parsed_value
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc


def canonicalize_json_string(value: str | None) -> str | None:
    """Normalize JSON string to canonical deterministic JSON representation."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    parsed = deserialize_json_value(stripped)
    return serialize_json_canonical(parsed)
