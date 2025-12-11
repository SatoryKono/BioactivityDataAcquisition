"""Value Objects for cryptographic primitives.

Contains type-safe wrappers for hashes and digests.
"""

from __future__ import annotations

import re
from typing import Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


class HashDigest:
    """Value Object for cryptographic hash digest (hex-encoded).

    Provides type safety for hash values throughout the system.
    Supports multiple algorithms with length validation.
    Immutable after creation.

    Attributes:
        value: Hex-encoded hash string (lowercase).
        algorithm: Algorithm identifier (default: 'blake2b_256').

    Supported algorithms:
        - blake2b_256: 64 hex chars (256 bits)
        - sha256: 64 hex chars (256 bits)
        - sha512: 128 hex chars (512 bits)
        - md5: 32 hex chars (128 bits)

    Examples:
        >>> HashDigest("a" * 64)  # Default blake2b_256
        HashDigest('aaaa...', algorithm='blake2b_256')
        >>> HashDigest("b" * 32, "md5")
        HashDigest('bbbb...', algorithm='md5')
        >>> HashDigest.blake2b_256("c" * 64)  # Factory method
        HashDigest('cccc...', algorithm='blake2b_256')
    """

    __slots__ = ("_value", "_algorithm")
    _value: str
    _algorithm: str
    _hex_pattern = re.compile(r"^[0-9a-f]+$")
    _known_lengths: dict[str, int] = {
        "blake2b_256": 64,  # 256 bits = 64 hex chars
        "sha256": 64,
        "sha512": 128,
        "md5": 32,
    }

    def __init__(self, value: str, algorithm: str = "blake2b_256") -> None:
        """Initialize HashDigest.

        Args:
            value: Hex-encoded hash string.
            algorithm: Algorithm identifier (default: blake2b_256).

        Raises:
            ValueError: If value is not valid hex or has wrong length for algorithm.
        """
        normalized = value.lower()
        if not self._hex_pattern.match(normalized):
            raise ValueError(f"HashDigest must be hex string: {value}")

        expected_len = self._known_lengths.get(algorithm)
        if expected_len is not None and len(normalized) != expected_len:
            raise ValueError(
                f"HashDigest length mismatch for {algorithm}: "
                f"expected {expected_len}, got {len(normalized)}"
            )

        object.__setattr__(self, "_value", normalized)
        object.__setattr__(self, "_algorithm", algorithm)

    def __setattr__(self, name: str, value: object) -> None:
        """Prevent modification after initialization (immutability guard)."""
        if hasattr(self, "_value"):
            raise AttributeError(
                f"Cannot modify immutable HashDigest: attribute {name!r}"
            )
        object.__setattr__(self, name, value)

    @property
    def value(self) -> str:
        """Hex-encoded hash string."""
        return self._value

    @property
    def algorithm(self) -> str:
        """Algorithm identifier."""
        return self._algorithm

    @property
    def is_blake2b(self) -> bool:
        """Check if this is a BLAKE2b-256 hash."""
        return self.algorithm == "blake2b_256"

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"HashDigest({self.value!r}, algorithm={self.algorithm!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, HashDigest):
            return self.value == other.value and self.algorithm == other.algorithm
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.value, self.algorithm))

    @classmethod
    def blake2b_256(cls, hex_value: str) -> Self:
        """Factory for BLAKE2b-256 hashes (backward compatibility).

        Args:
            hex_value: 64-character hex string.

        Returns:
            HashDigest with algorithm='blake2b_256'.
        """
        return cls(hex_value, "blake2b_256")

    @classmethod
    def from_hex(cls, hex_string: str, algorithm: str = "blake2b_256") -> Self:
        """Create HashDigest from hex string.

        Args:
            hex_string: Hex-encoded hash value.
            algorithm: Algorithm identifier (default: blake2b_256).

        Returns:
            HashDigest instance.
        """
        return cls(hex_string, algorithm)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            lambda v: cls(v) if isinstance(v, str) else v,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )
