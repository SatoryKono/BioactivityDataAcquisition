from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol

import pandas as pd


@dataclass
class NormalizationConfig:
    """
    Domain-level configuration for normalization.

    This is a pure domain object with no infrastructure dependencies.
    """

    case_sensitive_fields: list[str] = field(default_factory=list)
    id_fields: list[str] = field(default_factory=list)
    fields: list[dict[str, Any]] = field(default_factory=list)


class NormalizationConfigProvider(Protocol):
    """
    Protocol for objects that can provide normalization configuration.

    PipelineConfig from bioetl.config implements this implicitly.
    """

    @property
    def normalization(self) -> Any:
        """Return normalization section."""
        ...

    @property
    def fields(self) -> list[dict[str, Any]]:
        """Return fields configuration."""
        ...


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


class NormalizationServiceABC(ABC):
    """
    Сервис нормализации данных в DataFrame.
    """

    @abstractmethod
    def normalize_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Нормализует поля DataFrame согласно конфигурации."""
