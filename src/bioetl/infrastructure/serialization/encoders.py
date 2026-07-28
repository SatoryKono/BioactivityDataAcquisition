# basedpyright residual burn-down (shrink-only product surface).
"""JSON encoder implementations.

Provides two implementations of JsonEncoderPort:
1. StdLibJsonEncoder - Standard library json (always available)
2. OrjsonEncoder - orjson-based encoder (high performance, optional dependency)

Both implementations guarantee:
- Deterministic output (sorted keys when requested)
- Compact output (no extra whitespace)
- Unicode support

Usage:
    from bioetl.infrastructure.serialization import get_json_encoder

    encoder = get_json_encoder()
    json_str = encoder.dumps({"key": "value"})

Feature Flag:
    BIOETL_JSON_ENCODER=orjson  # Use orjson (default if available)
    BIOETL_JSON_ENCODER=stdlib  # Force stdlib json
"""

from __future__ import annotations

import json
import os
import types
from functools import lru_cache

from bioetl.domain.ports import JsonEncoderPort
from bioetl.domain.types import JsonDict

# Optional orjson import
try:
    import orjson as _orjson_module

    _orjson: types.ModuleType | None = _orjson_module
    orjson_available = True
except ImportError:
    _orjson = None
    orjson_available = False


def _to_ascii_json(json_text: str, *, sort_keys: bool) -> str:
    """Re-emit JSON text as compact ASCII JSON using valid JSON escapes."""
    return json.dumps(
        json.loads(json_text),
        sort_keys=sort_keys,
        separators=(",", ":"),
        ensure_ascii=True,
    )


class StdLibJsonEncoder:
    """Standard library json encoder implementation.

    Always available, provides baseline performance.
    Uses compact separators by default for minimal output size.
    """

    def dumps(
        self,
        obj: JsonDict | list[object],
        *,
        sort_keys: bool = True,
        ensure_ascii: bool = False,
    ) -> str:
        """Serialize object to JSON string.

        Args:
            obj: Dictionary or list to serialize
            sort_keys: If True, output keys in sorted order (default: True)
            ensure_ascii: If True, escape non-ASCII characters (default: False)

        Returns:
            Compact JSON string
        """
        return json.dumps(
            obj,
            sort_keys=sort_keys,
            ensure_ascii=ensure_ascii,
            separators=(",", ":"),
        )

    def dumps_canonical(
        self,
        obj: JsonDict,
    ) -> str:
        """Serialize object to canonical JSON for hashing.

        Canonical format: sorted keys, compact separators, ASCII-only.

        Args:
            obj: Dictionary to serialize

        Returns:
            Canonical JSON string suitable for hashing
        """
        return json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )

    def loads(self, data: str | bytes) -> JsonDict | list[object]:
        """Deserialize JSON string to Python object.

        Args:
            data: JSON string or bytes

        Returns:
            Deserialized Python object

        Raises:
            ValueError: If JSON is invalid
        """
        try:
            result: JsonDict | list[object] = json.loads(data)
            return result
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e


class OrjsonEncoder:
    """High-performance orjson-based encoder.

    Provides 2-10x performance improvement over stdlib json.
    Requires orjson package to be installed.

    Note: orjson.dumps() returns bytes, so we decode to str for API consistency.
    """

    def __init__(self) -> None:
        """Initialize OrjsonEncoder.

        Raises:
            ImportError: If orjson is not installed
        """
        if not orjson_available:
            raise ImportError(
                "orjson is not installed. Install with: pip install orjson"
            )

    def dumps(
        self,
        obj: JsonDict | list[object],
        *,
        sort_keys: bool = True,
        ensure_ascii: bool = False,
    ) -> str:
        """Serialize object to JSON string using orjson.

        Args:
            obj: Dictionary or list to serialize
            sort_keys: If True, output keys in sorted order (default: True)
            ensure_ascii: If True, escape non-ASCII characters (default: False)
                         Note: orjson always uses UTF-8, so this may require
                         post-processing for full ASCII escaping.

        Returns:
            Compact JSON string
        """
        assert _orjson is not None
        options = _orjson.OPT_SORT_KEYS if sort_keys else 0

        result: str = _orjson.dumps(obj, option=options).decode("utf-8")

        # orjson doesn't have ensure_ascii option
        if ensure_ascii:
            return _to_ascii_json(result, sort_keys=sort_keys)

        return result

    def dumps_canonical(
        self,
        obj: JsonDict,
    ) -> str:
        """Serialize object to canonical JSON for hashing.

        Canonical format: sorted keys, compact output, ASCII-only.

        Args:
            obj: Dictionary to serialize

        Returns:
            Canonical JSON string suitable for hashing
        """
        # For canonical output, we need ensure_ascii=True for hashing consistency
        assert _orjson is not None
        result: str = _orjson.dumps(obj, option=_orjson.OPT_SORT_KEYS).decode("utf-8")
        return _to_ascii_json(result, sort_keys=True)

    def loads(self, data: str | bytes) -> JsonDict | list[object]:
        """Deserialize JSON string to Python object using orjson.

        Args:
            data: JSON string or bytes

        Returns:
            Deserialized Python object

        Raises:
            ValueError: If JSON is invalid
        """
        assert _orjson is not None
        try:
            result: JsonDict | list[object] = _orjson.loads(data)
            return result
        except json.JSONDecodeError as e:
            # orjson.JSONDecodeError inherits from json.JSONDecodeError
            raise ValueError(f"Invalid JSON: {e}") from e


@lru_cache(maxsize=1)
def get_json_encoder(encoder_type: str | None = None) -> JsonEncoderPort:
    """Get the configured JSON encoder instance.

    Selection logic:
    1. Use provided encoder_type if not None
    2. If None, use orjson if available, otherwise stdlib

    Args:
        encoder_type: Optional encoder type ('orjson' or 'stdlib').

    Returns:
        JsonEncoderPort implementation

    Raises:
        ImportError: If orjson is requested but not installed
        ValueError: If unknown encoder type is specified
    """
    # Priority: explicit arg -> environment variable -> automatic default
    raw_type = encoder_type
    if raw_type is None:
        raw_type = os.getenv("BIOETL_JSON_ENCODER")
    effective_type = (raw_type or "").strip().lower()

    if effective_type == "orjson":
        if not orjson_available:
            raise ImportError(
                "JSON encoder 'orjson' requested but not installed. "
                "Install with: pip install orjson"
            )
        return OrjsonEncoder()

    if effective_type == "stdlib":
        return StdLibJsonEncoder()

    if effective_type and effective_type not in ("orjson", "stdlib", ""):
        raise ValueError(
            f"Unknown JSON encoder type: {effective_type}. "
            "Valid options: 'orjson', 'stdlib'"
        )

    # Default: use orjson if available, otherwise stdlib
    if orjson_available:
        return OrjsonEncoder()
    return StdLibJsonEncoder()


def reset_encoder_cache() -> None:
    """Clear the get_json_encoder cache.

    Used by tests to ensure env var changes (BIOETL_JSON_ENCODER) take effect
    when calling get_json_encoder() again.
    """
    get_json_encoder.cache_clear()


_ENCODER_API = (reset_encoder_cache,)

__all__ = [
    "orjson_available",
    "OrjsonEncoder",
    "StdLibJsonEncoder",
    "get_json_encoder",
    "reset_encoder_cache",
]
