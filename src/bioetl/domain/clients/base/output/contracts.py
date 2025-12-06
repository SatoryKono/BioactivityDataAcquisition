from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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

    Default factory: ``bioetl.infrastructure.output.factories.default_writer``.
    Implementations: ``CsvWriterImpl``, ``ParquetWriterImpl``.
    """

    @property
    @abstractmethod
    def atomic(self) -> bool:
        """Поддерживает ли атомарную запись."""

    @abstractmethod
    def write(
        self,
        df: pd.DataFrame,
        path: Path,
        *,
        column_order: list[str] | None = None,
    ) -> WriteResult:
        """Записывает DataFrame с учетом порядка колонок."""

    @abstractmethod
    def supports_format(self, fmt: str) -> bool:
        """Поддерживает ли формат (csv, parquet)."""


class MetadataWriterABC(ABC):
    """
    Запись метаданных и отчетов.

    Default factory: ``bioetl.infrastructure.output.factories.default_metadata_writer``.
    Implementations: ``MetadataWriterImpl``.
    """

    @abstractmethod
    def write_meta(self, meta: dict, path: Path) -> None:
        """Записывает метаданные (yaml)."""

    @abstractmethod
    def write_qc_report(
        self, df: pd.DataFrame, path: Path, *, min_coverage: float | None = None
    ) -> None:
        """Записывает отчет качества."""

    @abstractmethod
    def generate_checksums(self, paths: list[Path]) -> dict[str, str]:
        """Генерирует контрольные суммы файлов."""


class QualityReportABC(ABC):
    """Порт генератора QC-отчетов."""

    @abstractmethod
    def build_quality_report(
        self, df: pd.DataFrame, *, min_coverage: float
    ) -> pd.DataFrame:
        """Строит таблицу покрытия и базовых метрик по колонкам."""

    @abstractmethod
    def build_correlation_report(self, df: pd.DataFrame) -> pd.DataFrame:
        """Строит корреляционную матрицу по числовым колонкам."""


class OutputWriterABC(ABC):
    """
    Фасад для записи результатов пайплайна (данные + метаданные).

    Default factory: ``bioetl.infrastructure.output.factories.default_output_writer``.
    Implementations: ``UnifiedOutputWriter``.
    """

    @abstractmethod
    def write_result(
        self,
        df: pd.DataFrame,
        output_path: Path,
        entity_name: str,
        run_context: Any,
        *,
        column_order: list[str] | None = None,
    ) -> WriteResult:
        """
        Записывает результирующий DataFrame и сопутствующие артефакты,
        возвращая сведения о записи.
        """


__all__ = [
    "WriteResult",
    "WriterABC",
    "MetadataWriterABC",
    "QualityReportABC",
    "OutputWriterABC",
]
