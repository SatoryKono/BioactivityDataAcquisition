from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

from bioetl.domain.models import RunContext


@dataclass
class WriteResult:
    """Результат записи."""
    path: Path
    row_count: int
    checksum: str
    duration_sec: float


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


class OutputServiceABC(ABC):
    """Фасад записи результатов пайплайна."""

    @abstractmethod
    def write_result(
        self,
        df: pd.DataFrame,
        output_path: Path,
        entity_name: str,
        run_context: RunContext,
    ) -> WriteResult:
        """Записывает результат пайплайна и возвращает мета."""

