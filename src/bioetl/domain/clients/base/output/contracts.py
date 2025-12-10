"""Contracts for writing pipeline outputs and metadata."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

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

    Реализация предоставляется инфраструктурой через DI-контейнер.
    """

    @property
    @abstractmethod
    def is_atomic(self) -> bool:
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
    def has_format_support(self, fmt: str) -> bool:
        """Поддерживает ли формат (csv, parquet)."""


class MetadataWriterABC(ABC):
    """
    Запись метаданных и отчетов.

    Реализация предоставляется инфраструктурой через DI-контейнер.
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
    def build_checksums(self, paths: list[Path]) -> dict[str, str]:
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

    Реализация предоставляется инфраструктурой через DI-контейнер.
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


class RunMetadataBuilderProtocol(Protocol):
    """Port for building deterministic run metadata payloads."""

    def build_run_metadata(
        self, context: Any, write_result: WriteResult
    ) -> dict[str, Any]:
        """Build metadata for a completed run."""

    def build_dry_run_metadata(self, context: Any, row_count: int) -> dict[str, Any]:
        """Build metadata for a dry-run execution."""


@runtime_checkable
class OutputFrameConverterABC(Protocol):
    """DataFrame → DataFrame конвертер для пост-обработки перед записью."""

    def convert(self, df: pd.DataFrame) -> pd.DataFrame:
        """Преобразует DataFrame (rename/reorder/drop/enrich)."""


__all__ = [
    "WriteResult",
    "WriterABC",
    "MetadataWriterABC",
    "QualityReportABC",
    "OutputWriterABC",
    "RunMetadataBuilderProtocol",
    "OutputFrameConverterABC",
]
