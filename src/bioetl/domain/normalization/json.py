# basedpyright residual burn-down (shrink-only product surface).
"""Pure canonical JSON normalization helpers."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, TypeGuard, cast

from bioetl.domain.types.dq_contracts import DQDisposition

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
    "lookup_mapping_path",
    "serialize_json_canonical",
    "stable_json_hash",
    "to_jsonable",
]

_NON_ASCII_RE = re.compile(r"[^\x00-\x7F]")


def _escape_non_ascii(text: str) -> str:
    """Escape non-ASCII characters using JSON unicode escape format."""
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


def _validate_canonical_json_value(value: object) -> None:
    """Reject values whose canonical output would depend on the JSON backend."""
    _reject_numpy_like_array(value)
    if isinstance(value, float):
        _assert_finite_float(value)
        return
    if _is_json_scalar(value):
        return
    _validate_canonical_json_container(value)


def _reject_numpy_like_array(value: object) -> None:
    if not _is_numpy_like_array(value):
        return
    raise TypeError(
        "Canonical JSON serialization requires JSON-compatible values; "
        f"got {type(value).__name__}"
    )


def _validate_canonical_json_container(value: object) -> None:
    if isinstance(value, dict):
        _validate_json_mapping(value)
        return
    if _is_nested_json_sequence(value):
        _validate_json_sequence(cast(Sequence[object], value))
        return
    raise TypeError(
        f"Canonical JSON serialization requires JSON-compatible values; "
        f"got {type(value).__name__}"
    )


def _assert_finite_float(value: float) -> None:
    """Reject one non-finite float value."""
    if math.isfinite(value):
        return
    raise ValueError("Canonical JSON serialization does not allow NaN or Infinity")


def _is_json_scalar(value: object) -> bool:
    """Return whether *value* is a backend-independent JSON scalar."""
    return value is None or isinstance(value, (str, int, bool))


def _validate_json_mapping(value: dict[object, object]) -> None:
    """Validate mapping keys and values for canonical JSON serialization."""
    for key, nested_value in value.items():
        if not isinstance(key, str):
            raise TypeError("Canonical JSON serialization requires string keys")
        _validate_canonical_json_value(nested_value)


def _validate_json_sequence(value: Sequence[object]) -> None:
    """Validate every item in a JSON-like sequence."""
    for nested_value in value:
        _validate_canonical_json_value(nested_value)


def _is_nested_json_sequence(value: object) -> bool:
    """Return whether the value is a JSON-like sequence."""
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, bytearray))
        and not _is_numpy_like_array(value)
    )


def _is_numpy_like_array(value: object) -> bool:
    """Return whether value looks like a NumPy / pandas array, not JSON."""
    return (
        hasattr(value, "dtype")
        and hasattr(value, "shape")
        and not isinstance(value, (str, bytes, bytearray, memoryview))
    )


def lookup_mapping_path(
    mapping: Mapping[str, object],
    *path: str,
) -> object | None:
    """Read one nested mapping path using only mapping-shaped objects."""
    current: object = mapping
    for component in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(component)
    return current


def _convert_datetime(value: datetime) -> str:
    """Convert datetime to ISO format string."""
    return value.isoformat()


def _convert_dq_disposition(value: DQDisposition) -> str:
    """Convert DQDisposition to its value."""
    return value.value


def _convert_dataclass(value: object) -> dict[str, object]:
    """Convert dataclass to dictionary with recursive conversion."""
    # Caller guarantees a dataclass instance; asdict has no public input type.
    dataclass_value = cast(Any, value)  # Any: asdict over caller-guaranteed dataclass
    return {key: to_jsonable(item) for key, item in asdict(dataclass_value).items()}


def _convert_mapping(
    value: Mapping[Any, Any],  # Any: JSON normalization accepts arbitrary mappings
) -> dict[str, object]:
    """Convert mapping to dictionary with string keys and recursive conversion."""
    return {str(key): to_jsonable(item) for key, item in sorted(value.items())}


def _convert_sequence(
    value: Sequence[Any],  # Any: JSON normalization accepts arbitrary sequences
) -> list[object]:
    """Convert sequence to list with recursive conversion."""
    return [to_jsonable(item) for item in value]


def _is_primitive_sequence(value: object) -> bool:
    """Check if value is a string or bytes (should not be converted as sequence)."""
    return isinstance(value, (str, bytes, bytearray))


def _should_convert_as_sequence(
    value: object,
) -> TypeGuard[Sequence[Any]]:  # Any: JSON normalization accepts arbitrary sequences
    """Check if value should be converted as a sequence."""
    return isinstance(value, Sequence) and not _is_primitive_sequence(value)


def _convert_special_types(value: object) -> object | None:
    """Convert special types (datetime, DQDisposition) if applicable."""
    if isinstance(value, datetime):
        return _convert_datetime(value)
    if isinstance(value, DQDisposition):
        return _convert_dq_disposition(value)
    return None


def _convert_complex_types(value: object) -> object | None:
    """Convert complex types (dataclass, mapping, sequence) if applicable."""
    if is_dataclass(value) and not isinstance(value, type):
        return _convert_dataclass(value)
    if isinstance(value, Mapping):
        return _convert_mapping(value)
    if _should_convert_as_sequence(value):
        return _convert_sequence(value)
    return None


def to_jsonable(value: object) -> object:
    """Convert nested dataclasses, datetimes, and mappings into JSON-safe values."""
    converted = _convert_special_types(value)
    if converted is not None:
        return converted

    converted = _convert_complex_types(value)
    if converted is not None:
        return converted

    return value


def stable_json_hash(payload: object) -> str:
    """Return a SHA-256 hex digest of the canonical JSON form of ``payload``."""
    serialized = serialize_json_canonical(cast(JsonDict, to_jsonable(payload)))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def serialize_json_canonical(data: JsonDict | Sequence[object]) -> str:
    """Serialize data to deterministic canonical JSON string."""
    _validate_canonical_json_value(data)
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
