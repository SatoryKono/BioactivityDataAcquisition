"""
Value Objects for identifiers.

This module contains domain identifier types that ensure type safety
and validation for various entity identifiers used throughout the system.
"""

from __future__ import annotations

import re
import uuid
from typing import Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

__all__ = [
    "RunId",
    "StageName",
    "EntityName",
    "PipelineId",
    "ChemblId",
]


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
    """Value Object для имени стадии pipeline (snake_case).

    Используется для идентификации стадий в pipeline.

    Examples:
        - "fetch"
        - "transform"
        - "normalize_data"
    """

    __slots__ = ("_value",)
    _pattern = re.compile(r"^[a-z][a-z0-9_]*$")
    _max_length = 64

    def __init__(self, value: str) -> None:
        if not self._pattern.match(value):
            raise ValueError(f"StageName must be snake_case: {value}")
        if len(value) > self._max_length:
            raise ValueError(f"StageName too long: {len(value)} > {self._max_length}")
        self._value = value

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
