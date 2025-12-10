"""Contracts for writing pipeline outputs and metadata.

Tabular Data Abstractions:
    This module uses domain-level TabularData instead of pd.DataFrame.
    Infrastructure layer provides PandasAdapter implementations.

    See bioetl.domain.data for protocol definitions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from bioetl.domain.data import MutableTabularData, TabularData


@dataclass(frozen=True)
class WriteResult:
    """Result of a write operation."""

    path: Path
    row_count: int
    duration_sec: float
    checksum: str | None = None


class QualityReportABC(ABC):
    """QC report generator port.

    Uses domain-level TabularData abstraction.
    """

    @abstractmethod
    def build_quality_report(
        self, data: TabularData, *, min_coverage: float
    ) -> TabularData:
        """Build coverage and basic metrics table by columns.

        Args:
            data: Input tabular data.
            min_coverage: Minimum coverage threshold.

        Returns:
            Tabular data with quality metrics.
        """

    @abstractmethod
    def build_correlation_report(self, data: TabularData) -> TabularData:
        """Build correlation matrix for numeric columns.

        Args:
            data: Input tabular data.

        Returns:
            Tabular data with correlation matrix.
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
    """Tabular data converter for post-processing before write.

    Uses domain-level TabularData abstraction.
    """

    def convert(self, data: TabularData) -> MutableTabularData:
        """Convert tabular data (rename/reorder/drop/enrich).

        Args:
            data: Input tabular data.

        Returns:
            Transformed tabular data.
        """
        ...


__all__ = [
    "WriteResult",
    "QualityReportABC",
    "RunMetadataBuilderProtocol",
    "OutputFrameConverterABC",
]
