"""
Value Objects для идентификаторов.

Содержит типобезопасные идентификаторы для различных сущностей системы.
"""

from __future__ import annotations

import re
import uuid
from typing import Self

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


class StageName:
    """Value Object для имени стадии pipeline.

    Ограниченный набор допустимых стадий с поддержкой aliases.

    Allowed values:
        - "extract" - стадия извлечения данных
        - "transform" - стадия трансформации
        - "validate" - стадия валидации
        - "export" - стадия экспорта (alias: "load")

    Features:
        - Case-insensitive: StageName("EXTRACT") → StageName("extract")
        - Alias support: StageName("load") → StageName("export")
        - Enum-like access: StageName.EXTRACT, StageName.TRANSFORM, etc.

    Examples:
        >>> StageName("extract")
        StageName('extract')
        >>> StageName("EXTRACT")  # case-insensitive
        StageName('extract')
        >>> StageName("load")  # alias for export
        StageName('export')
        >>> StageName.EXTRACT
        StageName('extract')
    """

    __slots__ = ("_value",)

    # Allowed stage names
    _ALLOWED_VALUES: frozenset[str] = frozenset(
        {"extract", "transform", "validate", "export"}
    )

    # Aliases mapping (load → export for backward compatibility)
    _ALIASES: dict[str, str] = {"load": "export"}

    # Class-level constants (initialized after class definition)
    EXTRACT: StageName
    TRANSFORM: StageName
    VALIDATE: StageName
    EXPORT: StageName

    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"StageName requires str, got {type(value).__name__}")

        normalized = value.lower()

        # Resolve alias
        if normalized in self._ALIASES:
            normalized = self._ALIASES[normalized]

        if normalized not in self._ALLOWED_VALUES:
            allowed = sorted(self._ALLOWED_VALUES | set(self._ALIASES.keys()))
            raise ValueError(
                f"Invalid stage name: {value!r}. "
                f"Allowed values: {', '.join(allowed)}"
            )

        self._value = normalized

    @classmethod
    def all_values(cls) -> frozenset[str]:
        """Return all allowed stage name values."""
        return cls._ALLOWED_VALUES

    @property
    def value(self) -> str:
        """String representation of StageName."""
        return self._value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"StageName({self._value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, StageName):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    def __setattr__(self, name: str, value: object) -> None:
        """Prevent modification after initialization."""
        if hasattr(self, "_value"):
            raise AttributeError(
                f"Cannot modify immutable StageName: attribute {name!r}"
            )
        object.__setattr__(self, name, value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )


# Initialize enum-like class constants
StageName.EXTRACT = StageName("extract")
StageName.TRANSFORM = StageName("transform")
StageName.VALIDATE = StageName("validate")
StageName.EXPORT = StageName("export")


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
    """Value Object для идентификатора pipeline (формат: provider.entity).

    Examples:
        - "chembl.activity"
        - "pubchem.compound"
    """

    __slots__ = ("_value", "_provider", "_entity")
    _pattern = re.compile(r"^[a-z]+\.[a-z_]+$")

    def __init__(self, value: str) -> None:
        normalized = value.lower().strip()
        if not self._pattern.match(normalized):
            raise ValueError(
                f"Invalid PipelineId format: '{value}'. "
                f"Expected format: 'provider.entity' (e.g., 'chembl.activity')"
            )
        self._value = normalized
        parts = normalized.split(".", 1)
        self._provider = parts[0]
        self._entity = parts[1]

    @property
    def value(self) -> str:
        """String representation of PipelineId."""
        return self._value

    @property
    def provider(self) -> str:
        """Provider part of PipelineId (e.g., 'chembl')."""
        return self._provider

    @property
    def entity(self) -> str:
        """Entity part of PipelineId (e.g., 'activity')."""
        return self._entity

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
    def from_parts(cls, provider: str, entity: str) -> Self:
        """Создаёт PipelineId из отдельных компонентов."""
        return cls(f"{provider}.{entity}")

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls,
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


class ActivityId:
    """Value Object for ChEMBL activity identifier (numeric ID).

    Unlike ChemblId which uses CHEMBL123 format, ActivityId is a pure numeric
    identifier used in the ChEMBL activity table.

    Examples:
        >>> ActivityId(12345)
        ActivityId('12345')
        >>> ActivityId("67890")
        ActivityId('67890')
        >>> ActivityId("12345").numeric
        12345
    """

    __slots__ = ("_value",)
    _pattern = re.compile(r"^\d+$")

    def __init__(self, value: str | int) -> None:
        str_value = str(value)
        if not self._pattern.match(str_value):
            raise ValueError(f"Invalid ActivityId: {value}")
        self._value = str_value

    @property
    def value(self) -> str:
        """String representation of ActivityId."""
        return self._value

    @property
    def numeric(self) -> int:
        """Return numeric value of ActivityId."""
        return int(self._value)

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"ActivityId({self._value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ActivityId):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, ActivityId):
            return self.numeric < other.numeric
        return NotImplemented

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.union_schema(
                [core_schema.str_schema(), core_schema.int_schema()]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )
