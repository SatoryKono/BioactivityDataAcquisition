from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd

SchemaType = Any


@dataclass
class ValidationResult:
    """Результат валидации доменного уровня."""

    is_valid: bool
    errors: list[Any]
    warnings: list[str]
    validated_df: pd.DataFrame | None = None


class ValidatorABC(ABC):
    """Доменный интерфейс валидатора."""

    @abstractmethod
    def validate(self, df: pd.DataFrame) -> ValidationResult:
        """Валидирует DataFrame и возвращает результат проверки."""

    @abstractmethod
    def is_valid(self, df: pd.DataFrame) -> bool:
        """Упрощенная проверка валидности."""


class SchemaProviderABC(ABC):
    """Провайдер схем данных (без привязки к конкретной технологии)."""

    @abstractmethod
    def get_schema(self, name: str) -> SchemaType:
        """Возвращает схему по имени."""

    @abstractmethod
    def list_schemas(self) -> list[str]:
        """Возвращает список доступных схем."""

    @abstractmethod
    def get_schema_columns(self, name: str) -> list[str]:
        """Возвращает порядок колонок для схемы."""

    @abstractmethod
    def register(
        self,
        name: str,
        schema: SchemaType,
        *,
        column_order: list[str] | None = None,
    ) -> None:
        """Регистрирует новую схему."""


class ValidatorFactoryABC(Protocol):
    """Фабрика валидаторов под конкретную схему."""

    def create_validator(self, schema: SchemaType) -> ValidatorABC:
        """Создает валидатор для указанной схемы."""


class SchemaProviderFactoryABC(Protocol):
    """Фабрика провайдеров схем."""

    def create_schema_provider(self) -> SchemaProviderABC:
        """Создает провайдер схем."""
