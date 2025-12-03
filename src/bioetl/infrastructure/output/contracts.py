from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import pandas as pd


@dataclass
class WriteResult:
    """Результат записи."""
    path: Path
    row_count: int
    duration_sec: float
    checksum: str | None = None


class WriterABC(ABC):
    """
    Запись данных в файл.
    """

    @property
    @abstractmethod
    def atomic(self) -> bool:
        """Поддерживает ли атомарную запись."""

    @abstractmethod
    def write(self, df: pd.DataFrame, path: Path) -> WriteResult:
        """Записывает DataFrame."""

    @abstractmethod
    def supports_format(self, fmt: str) -> bool:
        """Поддерживает ли формат (csv, parquet)."""


class MetadataWriterABC(ABC):
    """
    Запись метаданных и отчетов.
    """

    @abstractmethod
    def write_meta(self, meta: dict, path: Path) -> None:
        """Записывает метаданные (yaml)."""

    @abstractmethod
    def write_qc_report(self, df: pd.DataFrame, path: Path) -> None:
        """Записывает отчет качества."""

    @abstractmethod
    def generate_checksums(self, paths: list[Path]) -> dict[str, str]:
        """Генерирует контрольные суммы файлов."""

