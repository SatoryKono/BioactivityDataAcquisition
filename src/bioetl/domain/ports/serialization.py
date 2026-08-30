"""JSON serialization port (Protocol) for pluggable encoders.

Implements RULES.md §1.1 - Ports & Adapters architecture.

This port abstracts JSON serialization operations to allow:
- Swapping between stdlib json and orjson for performance
- Consistent deterministic output (sort_keys=True equivalent)
- Feature flag control over serialization strategy

Requirements:
- Architecture (RULES 6.1 determinism): Deterministic writes for reproducibility (see REQ-GOV-002 / REQ-ARCH-003)
- All implementations MUST produce identical output for identical input
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from bioetl.domain.types import JsonDict


@runtime_checkable
class JsonEncoderPort(Protocol):
    """Port for JSON encoding operations.

    Implementations MUST guarantee:
    1. Deterministic output (sorted keys)
    2. Unicode support (non-ASCII characters preserved)
    3. Compact output (no extra whitespace)

    Canonical mode produces minimal output suitable for hashing:
    - Sorted keys
    - No whitespace
    - ASCII-only output (ensure_ascii=True)
    """

    def dumps(
        self,
        obj: JsonDict | list[Any],  # Any: JSON values are heterogeneous
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
            JSON string representation

        Note:
            Implementations should use compact separators (",", ":") by default.
        """
        ...

    def dumps_canonical(
        self,
        obj: JsonDict,  # Any: port contract allows heterogeneous record values
    ) -> str:  # Any: JSON values are heterogeneous
        """Serialize object to canonical JSON for hashing.

        Canonical JSON has:
        - Sorted keys
        - Compact separators (",", ":")
        - ASCII-only output (ensure_ascii=True)

        This is used for content hash generation to ensure deterministic hashes.

        Args:
            obj: Dictionary to serialize

        Returns:
            Canonical JSON string
        """
        ...

    def loads(
        self, data: str | bytes
    ) -> JsonDict | list[Any]:  # Any: JSON values are heterogeneous
        """Deserialize JSON string to Python object.

        Args:
            data: JSON string or bytes to deserialize

        Returns:
            Deserialized Python object (dict or list)

        Raises:
            ValueError: If JSON is invalid
        """
        ...


__all__ = ["JsonEncoderPort"]
