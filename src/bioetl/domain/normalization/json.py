"""Pure canonical JSON normalization helpers."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.types import JsonDict
else:
    JsonDict = dict[str, object]

try:
    import orjson

    _ORJSON_AVAILABLE = True
except ImportError:
    orjson = None  # type: ignore[assignment]
    _ORJSON_AVAILABLE = False

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
    )


def serialize_json_canonical(data: JsonDict | Sequence[object]) -> str:
    """Serialize data to deterministic canonical JSON string."""
    if _ORJSON_AVAILABLE:
        return _serialize_with_orjson(data, sort_keys=True, ensure_ascii=True)
    return _serialize_with_stdlib(data, sort_keys=True, ensure_ascii=True)


def deserialize_json_value(data: str | bytes) -> JsonDict | list[object]:
    """Deserialize JSON string or bytes to Python object."""
    if _ORJSON_AVAILABLE:
        assert orjson is not None
        try:
            return orjson.loads(data)
        except orjson.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc}") from exc
    try:
        return json.loads(data)
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
