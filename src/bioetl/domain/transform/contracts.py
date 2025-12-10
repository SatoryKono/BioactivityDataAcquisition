"""Domain-level transform contracts and DTOs.

Terminology:
    compute_row_fingerprint: Computes a hash of the entire row.
        Deprecated alias: hash_row (will be removed in v3.0).
    compute_entity_key: Computes a hash of the business key columns.
        Deprecated alias: hash_business_key (will be removed in v3.0).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Protocol
import warnings

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

    Terminology:
        compute_row_fingerprint: Canonical name for row hashing.
        compute_entity_key: Canonical name for business key hashing.
        hash_row: Deprecated alias for compute_row_fingerprint.
        hash_business_key: Deprecated alias for compute_entity_key.
    """

    @abstractmethod
    def compute_row_fingerprint(self, row: dict) -> str:
        """Вычисляет хеш-отпечаток строки как полного объекта.

        This is the canonical method name for row hashing.
        """

    @abstractmethod
    def compute_entity_key(self, row: dict, key_columns: list[str]) -> str:
        """Вычисляет хеш бизнес-ключа (выбранных колонок).

        This is the canonical method name for business key hashing.
        """

    @abstractmethod
    def add_hash_columns(
        self, df: pd.DataFrame, business_key_cols: list[str] | None = None
    ) -> pd.DataFrame:
        """Добавляет hash_row и hash_business_key колонки к DataFrame."""

    # =========================================================================
    # Deprecated aliases (will be removed in v3.0)
    # =========================================================================

    def hash_row(self, row: dict) -> str:
        """Deprecated: Use compute_row_fingerprint() instead.

        Will be removed in v3.0.
        """
        warnings.warn(
            "hash_row() is deprecated, use compute_row_fingerprint() instead. "
            "Will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.compute_row_fingerprint(row)

    def hash_business_key(self, row: dict, key_columns: list[str]) -> str:
        """Deprecated: Use compute_entity_key() instead.

        Will be removed in v3.0.
        """
        warnings.warn(
            "hash_business_key() is deprecated, use compute_entity_key() instead. "
            "Will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.compute_entity_key(row, key_columns)


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
