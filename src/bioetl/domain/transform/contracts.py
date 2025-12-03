from abc import ABC, abstractmethod
from typing import Any
import pandas as pd


class TransformerABC(ABC):
    """
    Интерфейс трансформации DataFrame.
    """

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Выполняет трансформацию."""

    @abstractmethod
    def validate_input(self, df: pd.DataFrame) -> None:
        """Проверяет входные данные."""

    @abstractmethod
    def validate_output(self, df: pd.DataFrame) -> None:
        """Проверяет выходные данные."""


class LookupEnricherABC(ABC):
    """
    Обогащение данных с использованием внешних справочников.
    """

    @abstractmethod
    def enrich(self, df: pd.DataFrame, lookup_key: str) -> pd.DataFrame:
        """Обогащает DataFrame."""

    @abstractmethod
    def load_lookup(self) -> pd.DataFrame:
        """Загружает справочник."""

    @abstractmethod
    def get_lookup_columns(self) -> list[str]:
        """Возвращает список колонок справочника."""


class BusinessKeyDeriverABC(ABC):
    """
    Вычисление бизнес-ключей.
    """

    @abstractmethod
    def derive(self, df: pd.DataFrame) -> pd.DataFrame:
        """Добавляет колонки с бизнес-ключами."""

    @abstractmethod
    def get_key_columns(self) -> list[str]:
        """Возвращает имена колонок бизнес-ключа."""

    @abstractmethod
    def validate_uniqueness(self, df: pd.DataFrame) -> bool:
        """Проверяет уникальность ключей."""


class DeduplicatorABC(ABC):
    """
    Устранение дубликатов.
    """

    @abstractmethod
    def deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Удаляет дубликаты."""

    @abstractmethod
    def get_duplicate_count(self, df: pd.DataFrame) -> int:
        """Возвращает количество дубликатов."""


class MergeStrategyABC(ABC):
    """
    Стратегия слияния записей.
    """

    @abstractmethod
    def merge(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """Сливает список записей в одну."""

    @property
    @abstractmethod
    def priority_key(self) -> str:
        """Ключ приоритета."""


class HasherABC(ABC):
    """
    Хеширование строк.
    """

    @property
    @abstractmethod
    def algorithm(self) -> str:
        """Используемый алгоритм (sha256)."""

    @abstractmethod
    def hash_row(self, row: pd.Series) -> str:
        """Хеширует строку Series."""

    @abstractmethod
    def hash_columns(self, df: pd.DataFrame, columns: list[str]) -> pd.Series:
        """Хеширует выбранные колонки DataFrame."""


class FieldNormalizerABC(ABC):
    """
    Интерфейс для нормализации отдельного поля.
    """

    @abstractmethod
    def normalize(self, value: Any) -> Any:
        """Нормализует значение."""


class NormalizationServiceABC(ABC):
    """
    Сервис нормализации данных в DataFrame.
    """

    @abstractmethod
    def normalize_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Нормализует поля DataFrame согласно конфигурации."""
