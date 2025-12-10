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
    Stateless сервис для вычисления и добавления хеш-сумм.

    Отвечает только за хеширование строк и бизнес-ключей.
    Не содержит stateful логики (индексы, timestamps).
    """

    @abstractmethod
    def hash_row(self, row: dict) -> str:
        """Вычисляет хеш строки как полного объекта."""

    @abstractmethod
    def hash_business_key(self, row: dict, key_columns: list[str]) -> str:
        """Вычисляет хеш бизнес-ключа (выбранных колонок)."""

    @abstractmethod
    def add_hash_columns(
        self, df: pd.DataFrame, business_key_cols: list[str] | None = None
    ) -> pd.DataFrame:
        """Добавляет hash_row и hash_business_key колонки к DataFrame."""


class TimestampProviderABC(ABC):
    """
    Провайдер временных меток для извлечения данных.

    Обеспечивает детерминированный timestamp в рамках сессии.
    """

    @abstractmethod
    def get_extraction_timestamp(self) -> datetime:
        """Возвращает timestamp извлечения данных."""


class IndexGeneratorABC(ABC):
    """
    Генератор последовательных индексов для строк данных.

    Stateful: сохраняет текущее значение счётчика между вызовами.
    """

    @abstractmethod
    def next_index(self) -> int:
        """Возвращает следующий индекс и увеличивает счётчик."""

    @abstractmethod
    def reset(self) -> None:
        """Сбрасывает счётчик в начальное состояние."""


__all__ = [
    "NormalizationConfig",
    "NormalizationConfigProviderProtocol",
    "HasherABC",
    "NormalizationServiceABC",
    "HashServiceABC",
    "TimestampProviderABC",
    "IndexGeneratorABC",
]
