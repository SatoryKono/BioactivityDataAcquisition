"""
Value Objects для ключевых идентификаторов.

Обеспечивают type safety и валидацию на уровне типов.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Self
from urllib.parse import urlparse
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


class HashDigest:
    """Value Object для BLAKE2b-256 хеш-дайджеста (64 hex символа)."""

    __slots__ = ("_value",)
    _pattern = re.compile(r"^[a-f0-9]{64}$")

    def __init__(self, value: str) -> None:
        normalized = value.lower()
        if not self._pattern.match(normalized):
            raise ValueError(
                f"Invalid HashDigest: '{value}'. "
                f"Expected 64 lowercase hex characters (BLAKE2b-256)"
            )
        self._value = normalized

    def __setattr__(self, name: str, value: object) -> None:
        if name == "_value" and hasattr(self, "_value"):
            raise AttributeError("HashDigest is immutable")
        super().__setattr__(name, value)

    @property
    def value(self) -> str:
        """String representation of HashDigest."""
        return self._value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"HashDigest({self._value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, HashDigest):
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


class HttpUrl:
    """Value Object для HTTP/HTTPS URL с валидацией и нормализацией."""

    __slots__ = ("_value", "_scheme", "_host", "_path")
    _allowed_schemes = frozenset({"http", "https"})

    def __init__(self, value: str) -> None:
        normalized = value.strip()
        if not normalized:
            raise ValueError("HttpUrl cannot be empty")

        parsed = urlparse(normalized)

        if not parsed.scheme:
            raise ValueError(f"HttpUrl must have a scheme: '{value}'")
        if parsed.scheme.lower() not in self._allowed_schemes:
            raise ValueError(
                f"HttpUrl scheme must be http or https, got: '{parsed.scheme}'"
            )
        if not parsed.netloc:
            raise ValueError(f"HttpUrl must have a host: '{value}'")

        self._scheme = parsed.scheme.lower()
        self._host = parsed.netloc.lower()
        # Нормализация path: удаляем trailing slash, если он не единственный символ
        path = parsed.path
        if path and path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        self._path = path or "/"

        # Сборка нормализованного URL
        query = f"?{parsed.query}" if parsed.query else ""
        fragment = f"#{parsed.fragment}" if parsed.fragment else ""
        self._value = f"{self._scheme}://{self._host}{self._path}{query}{fragment}"

    def __setattr__(self, name: str, value: object) -> None:
        if hasattr(self, "_value") and name in ("_value", "_scheme", "_host", "_path"):
            raise AttributeError("HttpUrl is immutable")
        super().__setattr__(name, value)

    @property
    def value(self) -> str:
        """Normalized URL string."""
        return self._value

    @property
    def scheme(self) -> str:
        """URL scheme (http or https)."""
        return self._scheme

    @property
    def host(self) -> str:
        """URL host (including port if specified)."""
        return self._host

    @property
    def path(self) -> str:
        """URL path (normalized, without trailing slash)."""
        return self._path

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"HttpUrl({self._value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, HttpUrl):
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


class Timestamp:
    """Value Object для timezone-aware timestamp (всегда UTC).

    Гарантирует, что все временные метки хранятся в UTC.
    """

    __slots__ = ("_value",)

    def __init__(self, value: datetime) -> None:
        if value.tzinfo is None:
            raise ValueError(
                "Timestamp must be timezone-aware. "
                "Use Timestamp.now() or Timestamp.from_iso() for convenience."
            )
        # Конвертируем в UTC для консистентности
        self._value = value.astimezone(timezone.utc)

    def __setattr__(self, name: str, value: object) -> None:
        if name == "_value" and hasattr(self, "_value"):
            raise AttributeError("Timestamp is immutable")
        super().__setattr__(name, value)

    @property
    def value(self) -> datetime:
        """Internal datetime object (timezone-aware, UTC)."""
        return self._value

    def to_iso(self) -> str:
        """Возвращает ISO 8601 строку с timezone."""
        return self._value.isoformat()

    def to_epoch(self) -> float:
        """Возвращает Unix timestamp (seconds since epoch)."""
        return self._value.timestamp()

    def __str__(self) -> str:
        return self.to_iso()

    def __repr__(self) -> str:
        return f"Timestamp({self.to_iso()!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Timestamp):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Timestamp):
            return self._value < other._value
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, Timestamp):
            return self._value <= other._value
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, Timestamp):
            return self._value > other._value
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, Timestamp):
            return self._value >= other._value
        return NotImplemented

    @classmethod
    def now(cls) -> Self:
        """Создаёт Timestamp с текущим временем в UTC."""
        return cls(datetime.now(timezone.utc))

    @classmethod
    def from_iso(cls, iso_string: str) -> Self:
        """Создаёт Timestamp из ISO 8601 строки.

        Args:
            iso_string: ISO 8601 formatted datetime string.
                       If no timezone info, assumes UTC.

        Returns:
            Timestamp instance.

        Raises:
            ValueError: If the string cannot be parsed.
        """
        try:
            dt = datetime.fromisoformat(iso_string)
        except ValueError as e:
            raise ValueError(f"Invalid ISO 8601 format: '{iso_string}'") from e

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return cls(dt)

    @classmethod
    def from_epoch(cls, epoch: float) -> Self:
        """Создаёт Timestamp из Unix timestamp."""
        return cls(datetime.fromtimestamp(epoch, tz=timezone.utc))

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls.from_iso,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda ts: ts.to_iso()
            ),
        )
