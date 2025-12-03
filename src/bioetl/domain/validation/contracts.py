from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
import pandas as pd
import pandera.pandas as pa


@dataclass
class ValidationResult:
    """Результат валидации."""
    is_valid: bool
    errors: list[Any]  # ValidationError
    warnings: list[str]


class ValidatorABC(ABC):
    """
    Валидация данных.
    """

    @abstractmethod
    def validate(self, df: pd.DataFrame) -> ValidationResult:
        """Валидирует DataFrame, возвращает результат."""

    @abstractmethod
    def is_valid(self, df: pd.DataFrame) -> bool:
        """Простая проверка валидности."""


class SchemaProviderABC(ABC):
    """
    Провайдер схем данных.
    """

    @abstractmethod
    def get_schema(self, name: str) -> type[pa.DataFrameModel]:
        """Возвращает класс схемы по имени."""

    @abstractmethod
    def list_schemas(self) -> list[str]:
        """Возвращает список доступных схем."""

    @abstractmethod
    def register(self, name: str, schema: type[pa.DataFrameModel]) -> None:
        """Регистрирует новую схему."""

    @abstractmethod
    def register_output_descriptor(
        self, name: str, descriptor: "OutputSchemaDescriptor"
    ) -> None:
        """Регистрирует дескриптор выходной схемы."""

    @abstractmethod
    def get_output_descriptor(
        self, name: str
    ) -> "OutputSchemaDescriptor" | None:
        """Возвращает дескриптор выходной схемы, если он зарегистрирован."""


@dataclass
class OutputSchemaDescriptor:
    """Описывает выходной порядок и подмножество колонок."""

    schema: type[pa.DataFrameModel]
    column_order: list[str]
