"""Domain-level transform contracts and DTOs."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Protocol

import pandas as pd

# Import the canonical NormalizationConfig from configs.normalization
from bioetl.domain.configs.normalization import NormalizationConfig


class NormalizationConfigProviderProtocol(Protocol):
    """Provides normalization configuration context for services."""

    def get_normalization(self) -> Any:
        """Return normalization section."""

    def get_fields(self) -> list[dict[str, Any]]:
        """Return field configuration for normalization."""

    @property
    def serialization_mode(self) -> str:
        """Return configured serialization mode for nested structures."""


class HasherABC(ABC):
    """Хеширование строк."""

    def get_algorithm(self) -> str:
        """Используемый алгоритм (по умолчанию blake2b_256)."""

        return "blake2b_256"

    @abstractmethod
    def compute_hash_row(self, row: pd.Series) -> str:
        """Хеширует строку Series."""

    @abstractmethod
    def compute_hash_columns(self, df: pd.DataFrame, columns: list[str]) -> pd.Series:
        """Хеширует выбранные колонки DataFrame."""


class NormalizationServiceABC(ABC):
    """Сервис нормализации данных."""

    @abstractmethod
    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Пакетно нормализует DataFrame и приводит числовые столбцы."""

    @abstractmethod
    def normalize_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Нормализует одну запись."""

    @abstractmethod
    def ensure_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Приводит числовые столбцы к nullable pandas dtypes."""


class HashServiceABC(ABC):
    """
    Фасад для вычисления и добавления хеш-сумм и служебных колонок.
    """

    @abstractmethod
    def add_hash_columns(
        self, df: pd.DataFrame, business_key_cols: list[str] | None = None
    ) -> pd.DataFrame:
        """Добавляет hash_row и hash_business_key с учетом бизнес-ключа."""

    @abstractmethod
    def add_index_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """Добавляет порядковый индекс строк (int, начиная с 0)."""

    @abstractmethod
    def add_database_version_column(
        self, df: pd.DataFrame, database_version: str
    ) -> pd.DataFrame:
        """Добавляет колонку database_version."""

    @abstractmethod
    def add_fulldate_column(
        self, df: pd.DataFrame, timestamp: datetime | None = None
    ) -> pd.DataFrame:
        """Добавляет колонку extracted_at (UTC ISO-8601) для детерминизма."""

    @abstractmethod
    def reset_state(self) -> None:
        """Сбрасывает внутреннее состояние между запусками."""


__all__ = [
    "NormalizationConfig",
    "NormalizationConfigProviderProtocol",
    "HasherABC",
    "NormalizationServiceABC",
    "HashServiceABC",
]
