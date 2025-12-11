"""Ports for output components (domain layer).

This module defines the interfaces for output-related components
following the hexagonal architecture pattern.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import pandas as pd

    from bioetl.domain.clients.base.output.contracts import WriteResult
    from bioetl.domain.configs import QcConfig
    from bioetl.domain.models import RunContext


class DataWriterPort(Protocol):
    """Port for writing DataFrame to various formats (parquet, csv, json).

    Implementations handle format-specific serialization without
    knowledge of QC reports, metadata, or checksums.
    """

    def write(
        self,
        df: Any,
        path: Path,
        *,
        column_order: list[str] | None = None,
    ) -> "WriteResult":
        """Write DataFrame to the specified path.

        Args:
            df: DataFrame to write.
            path: Target file path.
            column_order: Optional column ordering.

        Returns:
            WriteResult with path, row_count, duration.
        """
        ...

    def has_format_support(self, fmt: str) -> bool:
        """Check if this writer supports the given format.

        Args:
            fmt: Format name (e.g., 'csv', 'parquet', 'json').

        Returns:
            True if format is supported.
        """
        ...


class QcReportGeneratorPort(ABC):
    """Port for generating QC (quality control) reports.

    Implementations build quality and correlation reports
    without knowledge of file writing or metadata.
    """

    @abstractmethod
    def build_quality_report(self, df: Any, *, min_coverage: float) -> Any:
        """Build quality metrics report for DataFrame columns.

        Args:
            df: Source DataFrame.
            min_coverage: Minimum coverage threshold.

        Returns:
            DataFrame with column-level quality metrics.
        """

    @abstractmethod
    def build_correlation_report(self, df: Any) -> Any:
        """Build correlation matrix for numeric columns.

        Args:
            df: Source DataFrame.

        Returns:
            DataFrame with correlation matrix.
        """


class MetadataBuilderPort(ABC):
    """Port for building run metadata.

    Implementations construct metadata dictionaries without
    knowledge of how they will be persisted.
    """

    @abstractmethod
    def build_run_metadata(
        self,
        context: "RunContext",
        result: "WriteResult",
        *,
        qc_artifacts: list[Path] | None = None,
        qc_checksums: dict[str, str] | None = None,
        qc_config: "QcConfig | None" = None,
    ) -> dict[str, Any]:
        """Build metadata for a completed pipeline run.

        Args:
            context: Run context with execution details.
            result: Write result with path and checksum.
            qc_artifacts: List of QC artifact paths.
            qc_checksums: Checksums for QC artifacts.
            qc_config: QC configuration used.

        Returns:
            Metadata dictionary ready for serialization.
        """

    @abstractmethod
    def build_dry_run_metadata(
        self, context: "RunContext", row_count: int
    ) -> dict[str, Any]:
        """Build metadata for a dry-run execution.

        Args:
            context: Run context.
            row_count: Number of rows that would be written.

        Returns:
            Metadata dictionary for dry run.
        """


class MetadataWriterPort(Protocol):
    """Port for persisting metadata to storage.

    Implementations handle serialization format (YAML, JSON)
    and atomic writes without knowledge of metadata structure.
    """

    def write_meta(self, meta: dict[str, Any], path: Path) -> None:
        """Write metadata dictionary to file.

        Args:
            meta: Metadata dictionary.
            path: Target file path.
        """
        ...


class ChecksumCalculatorPort(ABC):
    """Port for calculating file checksums.

    Implementations provide hash computation without
    knowledge of file formats or metadata.
    """

    @abstractmethod
    def compute_checksum(self, path: Path) -> str:
        """Compute checksum for a single file.

        Args:
            path: Path to file.

        Returns:
            Hex-encoded checksum string.
        """

    @abstractmethod
    def compute_checksums(self, paths: list[Path]) -> dict[str, str]:
        """Compute checksums for multiple files.

        Args:
            paths: List of file paths.

        Returns:
            Dict mapping filename to checksum.
        """


class QcArtifactWriterPort(Protocol):
    """Port for writing QC artifacts (CSV reports).

    Implementations handle atomic CSV writing without
    knowledge of QC report generation logic.
    """

    def write_qc_csv(self, df: pd.DataFrame, path: Path) -> Path:
        """Write QC DataFrame to CSV atomically.

        Args:
            df: QC report DataFrame.
            path: Target file path.

        Returns:
            Path to written file.
        """
        ...


__all__ = [
    "ChecksumCalculatorPort",
    "DataWriterPort",
    "MetadataBuilderPort",
    "MetadataWriterPort",
    "QcArtifactWriterPort",
    "QcReportGeneratorPort",
]
