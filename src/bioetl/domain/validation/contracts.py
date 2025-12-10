"""Domain contracts for validation services and schema providers.

Tabular Data Abstractions:
    This module uses domain-level TabularData instead of pd.DataFrame.
    Infrastructure layer provides PandasAdapter implementations.

    See bioetl.domain.data for protocol definitions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from bioetl.domain.data import TabularData

schema_type = Any


@dataclass
class ValidationResult:
    """Domain-level validation result.

    Attributes:
        is_valid: Whether validation passed.
        errors: List of validation errors.
        warnings: List of validation warnings.
        validated_data: Validated tabular data (if validation passed).
    """

    is_valid: bool
    errors: list[Any]
    warnings: list[str]
    validated_data: TabularData | None = None


class ValidatorABC(ABC):
    """Domain validator interface.

    Uses domain-level TabularData abstraction.
    """

    @abstractmethod
    def validate(self, data: TabularData) -> ValidationResult:
        """Validate tabular data and return validation result.

        Args:
            data: Tabular data to validate.

        Returns:
            ValidationResult with validation status and details.
        """

    @abstractmethod
    def is_valid(self, data: TabularData) -> bool:
        """Simplified validity check.

        Args:
            data: Tabular data to validate.

        Returns:
            True if data passes validation.
        """


class SchemaProviderABC(ABC):
    """Провайдер схем данных (без привязки к конкретной технологии)."""

    @abstractmethod
    def get_schema(self, name: str) -> schema_type:
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
        schema: schema_type,
        *,
        column_order: list[str] | None = None,
    ) -> None:
        """Регистрирует новую схему."""


@runtime_checkable
class ValidatorFactoryABC(Protocol):
    """Фабрика валидаторов под конкретную схему."""

    def create_validator(self, schema: schema_type) -> ValidatorABC:
        """Создает валидатор для указанной схемы."""


@runtime_checkable
class SchemaProviderFactoryABC(Protocol):
    """Фабрика провайдеров схем."""

    def create_schema_provider(self) -> SchemaProviderABC:
        """Создает провайдер схем."""
