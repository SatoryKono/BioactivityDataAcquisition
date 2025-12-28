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
from typing import Any

from bioetl.domain.ports import JsonEncoderPort

# Optional orjson import
_orjson: types.ModuleType | None
try:
    import orjson as _orjson

    ORJSON_AVAILABLE = True
except ImportError:
    _orjson = None
    ORJSON_AVAILABLE = False


class StdLibJsonEncoder:
    """Standard library json encoder implementation.

    Always available, provides baseline performance.
    Uses compact separators by default for minimal output size.
    """

    def dumps(
        self,
        obj: dict[str, Any] | list[Any],
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

    def dumps_canonical(self, obj: dict[str, Any]) -> str:
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

    def loads(self, data: str | bytes) -> dict[str, Any] | list[Any]:
        """Deserialize JSON string to Python object.

        Args:
            data: JSON string or bytes

        Returns:
            Deserialized Python object

        Raises:
            ValueError: If JSON is invalid
        """
        try:
            result: dict[str, Any] | list[Any] = json.loads(data)
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
        if not ORJSON_AVAILABLE:
            raise ImportError(
                "orjson is not installed. Install with: pip install orjson"
            )

    def dumps(
        self,
        obj: dict[str, Any] | list[Any],
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
        # For ASCII-only output, we need to escape non-ASCII chars
        if ensure_ascii:
            return result.encode("unicode_escape").decode("ascii")

        return result

    def dumps_canonical(self, obj: dict[str, Any]) -> str:
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
        # Escape non-ASCII for canonical form
        return result.encode("unicode_escape").decode("ascii")

    def loads(self, data: str | bytes) -> dict[str, Any] | list[Any]:
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
            result: dict[str, Any] | list[Any] = _orjson.loads(data)
            return result
        except json.JSONDecodeError as e:
            # orjson.JSONDecodeError inherits from json.JSONDecodeError
            raise ValueError(f"Invalid JSON: {e}") from e


@lru_cache(maxsize=1)
def get_json_encoder() -> JsonEncoderPort:
    """Get the configured JSON encoder instance.

    Selection logic:
    1. Check BIOETL_JSON_ENCODER environment variable
       - "orjson": Use OrjsonEncoder (error if not available)
       - "stdlib": Use StdLibJsonEncoder
    2. If not set, use orjson if available, otherwise stdlib

    Returns:
        JsonEncoderPort implementation

    Raises:
        ImportError: If orjson is requested but not installed
        ValueError: If unknown encoder type is specified
    """
    encoder_type = os.environ.get("BIOETL_JSON_ENCODER", "").lower()

    if encoder_type == "orjson":
        if not ORJSON_AVAILABLE:
            raise ImportError(
                "BIOETL_JSON_ENCODER=orjson but orjson is not installed. "
                "Install with: pip install orjson"
            )
        return OrjsonEncoder()

    if encoder_type == "stdlib":
        return StdLibJsonEncoder()

    if encoder_type and encoder_type not in ("orjson", "stdlib", ""):
        raise ValueError(
            f"Unknown JSON encoder type: {encoder_type}. "
            "Valid options: 'orjson', 'stdlib'"
        )

    # Default: use orjson if available, otherwise stdlib
    if ORJSON_AVAILABLE:
        return OrjsonEncoder()
    return StdLibJsonEncoder()


def reset_encoder_cache() -> None:
    """Clear the encoder cache (for testing).

    Call this after changing BIOETL_JSON_ENCODER environment variable
    to get a fresh encoder instance.
    """
    get_json_encoder.cache_clear()


__all__ = [
    "ORJSON_AVAILABLE",
    "OrjsonEncoder",
    "StdLibJsonEncoder",
    "get_json_encoder",
    "reset_encoder_cache",
]
