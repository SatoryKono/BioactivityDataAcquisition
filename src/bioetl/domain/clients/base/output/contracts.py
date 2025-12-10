"""Contracts for writing pipeline outputs and metadata."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import pandas as pd


@dataclass(frozen=True)
class WriteResult:
    """Result of a write operation."""

    path: Path
    row_count: int
    duration_sec: float
    checksum: str | None = None


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
        ...


__all__ = [
    "WriteResult",
    "QualityReportABC",
    "RunMetadataBuilderProtocol",
    "OutputFrameConverterABC",
]
