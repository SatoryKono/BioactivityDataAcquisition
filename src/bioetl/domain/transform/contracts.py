"""Domain-level transform contracts and DTOs."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Protocol

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


class BaseNormalizationServiceABC(ABC):
    """
    Базовый контракт сервисов нормализации.

    Предоставляет вспомогательные методы для нормализации скалярных и
    контейнерных значений, а также принудительного приведения типов
    числовых столбцов. Default factory:
    ``bioetl.infrastructure.transform.factories.default_base_normalization_service``.
    Реализации: ``BaseNormalizationServiceImpl``.
    """

    @abstractmethod
    def ensure_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Приводит числовые столбцы к nullable pandas dtypes."""

    @abstractmethod
    def _resolve_mode(self, field_name: str) -> str:
        """Определяет режим нормализации для поля."""

    @abstractmethod
    def _normalize_value(
        self,
        value: Any,
        dtype: str | None,
        normalizer: Callable[[Any], Any],
        field_name: str,
        *,
        allow_container_normalizer: bool = False,
        serialize_with_value_normalizer: bool = True,
    ) -> Any:
        """Нормализует значение с учетом типа и стратегии сериализации."""

    @abstractmethod
    def _process_list(
        self,
        value: Any,
        normalizer: Callable[[Any], Any],
        field_name: str,
        *,
        serialize_with_value_normalizer: bool = True,
    ) -> Any:
        """Нормализует список значений согласно конфигурации поля."""

    @abstractmethod
    def _process_dict(
        self, value: Any, normalizer: Callable[[Any], Any], field_name: str
    ) -> Any:
        """Нормализует словарь значений согласно конфигурации поля."""

    @abstractmethod
    def _normalize_container_item(
        self, item: Any, normalizer: Callable[[Any], Any]
    ) -> Any:
        """Нормализует элемент контейнера (dict/list/tuple)."""


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
    """
    Сервис нормализации данных в DataFrame.

    Обязательные операции:
    - apply_normalize: нормализация единичной записи
    - apply_normalize_fields: пакетная нормализация DataFrame по конфигурации
    - apply_normalize_dataframe: совместимый алиас для apply_normalize_fields
    - apply_normalize_batch: пакетная нормализация чанка
    - apply_normalize_series: нормализация столбца по конфигурации
    """

    @abstractmethod
    def apply_normalize(self, raw: pd.Series | dict[str, Any]) -> dict[str, Any]:
        """Нормализует одиночную запись или Series."""

    @abstractmethod
    def apply_normalize_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Нормализует поля DataFrame согласно конфигурации.
        Deprecated: use apply_normalize_dataframe instead.
        """

    def apply_normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Нормализует поля DataFrame (alias to apply_normalize_fields)."""
        return self.apply_normalize_fields(df)

    @abstractmethod
    def apply_normalize_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Нормализует DataFrame чанками или целиком."""

    @abstractmethod
    def apply_normalize_series(
        self,
        series: pd.Series,
        field_cfg: dict[str, Any],
    ) -> pd.Series:
        """Нормализует отдельную серию согласно полю конфигурации."""


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
    "BaseNormalizationServiceABC",
    "NormalizationConfig",
    "NormalizationConfigProviderProtocol",
    "HasherABC",
    "NormalizationServiceABC",
    "HashServiceABC",
]
