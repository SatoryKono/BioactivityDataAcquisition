"""
Value Objects для ключевых идентификаторов.

Обеспечивают type safety и валидацию на уровне типов.
"""

from __future__ import annotations

import re
from typing import Self
import uuid

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


class RunId:
    """Value Object для идентификатора запуска pipeline (UUID v4)."""

    __slots__ = ("_value",)
    _pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )

    def __init__(self, value: str) -> None:
        normalized = value.lower()
        if not self._pattern.match(normalized):
            raise ValueError(f"Invalid RunId format: {value}")
        self._value = normalized

    @property
    def value(self) -> str:
        """String representation of RunId."""
        return self._value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"RunId({self._value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, RunId):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    @classmethod
    def generate(cls) -> Self:
        """Генерирует новый уникальный RunId."""
        return cls(str(uuid.uuid4()))

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )


class EntityName:
    """Value Object для имени сущности (snake_case)."""

    __slots__ = ("_value",)
    _pattern = re.compile(r"^[a-z][a-z0-9_]*$")
    _max_length = 64

    def __init__(self, value: str) -> None:
        if not self._pattern.match(value):
            raise ValueError(f"EntityName must be snake_case: {value}")
        if len(value) > self._max_length:
            raise ValueError(f"EntityName too long: {len(value)} > {self._max_length}")
        self._value = value

    @property
    def value(self) -> str:
        """String representation of EntityName."""
        return self._value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"EntityName({self._value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, EntityName):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )


class PipelineId:
    """Value Object для идентификатора pipeline."""

    __slots__ = ("_value",)
    _max_length = 128

    def __init__(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("PipelineId must be a non-empty string")
        normalized = value.strip()
        if len(normalized) > self._max_length:
            raise ValueError(
                f"PipelineId too long: {len(normalized)} > {self._max_length}"
            )
        self._value = normalized

    @property
    def value(self) -> str:
        """String representation of PipelineId."""
        return self._value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"PipelineId({self._value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PipelineId):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )


class HashDigest:
    """Value Object for cryptographic hash digest (hex-encoded).

    Provides type safety for hash values throughout the system.
    Supports common algorithms: blake2b_256, sha256, md5.

    Attributes:
        value: Hex-encoded hash string (lowercase).
        algorithm: Algorithm identifier (e.g., 'blake2b_256').
    """

    __slots__ = ("_value", "_algorithm")
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

        self._value = normalized
        self._algorithm = algorithm

    @property
    def value(self) -> str:
        """Hex-encoded hash string."""
        return self._value

    @property
    def algorithm(self) -> str:
        """Algorithm identifier."""
        return self._algorithm

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"HashDigest({self._value!r}, algorithm={self._algorithm!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, HashDigest):
            return self._value == other._value and self._algorithm == other._algorithm
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self._value, self._algorithm))

    @classmethod
    def from_hex(cls, hex_string: str, algorithm: str = "blake2b_256") -> Self:
        """Create HashDigest from hex string."""
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


class ChemblId:
    """Value Object для ChEMBL идентификатора (формат CHEMBL123)."""

    __slots__ = ("_value",)
    _pattern = re.compile(r"^CHEMBL\d+$")

    def __init__(self, value: str) -> None:
        normalized = value.upper()
        if not self._pattern.match(normalized):
            raise ValueError(f"Invalid ChemblId: {value}")
        self._value = normalized

    @property
    def value(self) -> str:
        """String representation of ChemblId."""
        return self._value

    @property
    def numeric_id(self) -> int:
        """Возвращает числовую часть идентификатора."""
        return int(self._value[6:])

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"ChemblId({self._value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ChemblId):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, ChemblId):
            return self.numeric_id < other.numeric_id
        return NotImplemented

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )
