"""Unified loader facade for pipeline outputs.

This module provides UnifiedLoaderImpl - a facade that coordinates
multiple output components following the Single Responsibility Principle.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from bioetl.domain.clients.base.output.contracts import (
    OutputFrameConverterABC,
    WriteResult,
)
from bioetl.domain.configs import DeterminismConfig, QcConfig
from bioetl.domain.models import RunContext
from bioetl.domain.observability import MetricsPortABC
from bioetl.domain.pipelines.contracts import LoaderABC
from bioetl.domain.ports.output import (
    ChecksumCalculatorPort,
    DataWriterPort,
    MetadataBuilderPort,
    MetadataWriterPort,
    QcReportGeneratorPort,
)
from bioetl.infrastructure.files.atomic import AtomicFileOperation
from bioetl.infrastructure.output.column_order import apply_column_order
from bioetl.infrastructure.output.components.checksum_calculator import (
    ChecksumCalculator,
)
from bioetl.infrastructure.output.components.metadata_builder import MetadataBuilder
from bioetl.infrastructure.output.components.qc_artifact_writer import QcArtifactWriter
from bioetl.infrastructure.settings.metrics import MetricName


class UnifiedLoaderImpl(LoaderABC):
    """
    Facade for writing pipeline results.

    Coordinates multiple components:
    - DataWriter: writes data files (parquet, csv)
    - QcReportGenerator: generates quality reports
    - MetadataBuilder: constructs run metadata
    - ChecksumCalculator: computes file checksums
    - QcArtifactWriter: writes QC CSV files

    Each component has a single responsibility and can be
    replaced independently via dependency injection.
    """

    def __init__(
        self,
        data_writer: DataWriterPort,
        metadata_writer: MetadataWriterPort,
        qc_report_generator: QcReportGeneratorPort,
        config: DeterminismConfig,
        qc_config: QcConfig | None = None,
        atomic_op: AtomicFileOperation | None = None,
        metrics: MetricsPortABC | None = None,
        converter: OutputFrameConverterABC | None = None,
        *,
        checksum_calculator: ChecksumCalculatorPort | None = None,
        metadata_builder: MetadataBuilderPort | None = None,
        qc_artifact_writer: QcArtifactWriter | None = None,
    ) -> None:
        """Initialize the unified loader facade.

        Args:
            data_writer: Component for writing data files.
            metadata_writer: Component for persisting metadata.
            qc_report_generator: Component for generating QC reports.
            config: Determinism configuration.
            qc_config: QC report configuration.
            atomic_op: Atomic file operation handler.
            metrics: Metrics port for observability.
            converter: Optional DataFrame converter.
            checksum_calculator: Component for computing checksums.
            metadata_builder: Component for building metadata dicts.
            qc_artifact_writer: Component for writing QC CSV files.
        """
        # Core dependencies
        self._data_writer = data_writer
        self._metadata_writer = metadata_writer
        self._qc_report_generator = qc_report_generator
        self._config = config
        self._qc_config = qc_config or QcConfig()
        self._atomic_op = atomic_op or AtomicFileOperation()
        self._metrics = metrics
        self._converter = converter

        # Component dependencies (with defaults)
        self._checksum_calculator = checksum_calculator or ChecksumCalculator()
        self._metadata_builder = metadata_builder or MetadataBuilder()
        self._qc_artifact_writer = qc_artifact_writer or QcArtifactWriter(
            self._atomic_op
        )

    def load(
        self,
        df: pd.DataFrame,
        output_path: Path,
        context: RunContext,
        *,
        column_order: list[str] | None = None,
    ) -> WriteResult:
        """Load DataFrame to output path with full pipeline processing.

        Args:
            df: DataFrame to write.
            output_path: Output directory path.
            context: Run context with execution details.
            column_order: Optional column ordering.

        Returns:
            WriteResult with path, row_count, checksum.
        """
        return self._write_result(
            df=df,
            output_path=output_path,
            entity_name=str(context.entity_name),
            run_context=context,
            column_order=column_order,
        )

    def write_metadata(self, meta: dict, path: Path) -> None:
        """Write metadata dictionary to file.

        Args:
            meta: Metadata dictionary.
            path: Target file path.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        self._metadata_writer.write_meta(meta, path)

    def write_qc_report(self, df: pd.DataFrame, path: Path) -> None:
        """Write a pre-built QC report to file.

        Args:
            df: QC report DataFrame.
            path: Target file path.
        """
        self._qc_artifact_writer.write_qc_csv(df, path)

    def _write_result(
        self,
        df: pd.DataFrame,
        output_path: Path,
        entity_name: str,
        run_context: RunContext,
        *,
        column_order: list[str] | None = None,
    ) -> WriteResult:
        """Core write logic coordinating all components.

        Args:
            df: DataFrame to write.
            output_path: Output directory.
            entity_name: Name of the entity being written.
            run_context: Run context.
            column_order: Optional column ordering.

        Returns:
            WriteResult with final checksum.
        """
        try:
            output_path.mkdir(parents=True, exist_ok=True)

            # 1. Prepare DataFrame (column order + determinism)
            df_prepared = apply_column_order(df, column_order)
            df_prepared = self._stable_sort(df_prepared, run_context, column_order)

            # 2. Apply converter if provided
            if self._converter is not None:
                df_prepared = self._converter.convert(df_prepared)

            column_order_to_write = list(df_prepared.columns)

            # 3. Write data file atomically
            data_path = output_path / f"{entity_name}.csv"
            inner_result: WriteResult | None = None

            def _write_wrapper(path: Path) -> None:
                nonlocal inner_result
                inner_result = self._data_writer.write(
                    df_prepared, path, column_order=column_order_to_write
                )

            self._atomic_op.write_atomic(data_path, _write_wrapper)

            if inner_result is None:
                raise RuntimeError("Inner writer did not return result")

            # 4. Compute checksum for data file
            checksum = self._checksum_calculator.compute_checksum(data_path)

            final_result = WriteResult(
                path=data_path,
                row_count=inner_result.row_count,
                duration_sec=inner_result.duration_sec,
                checksum=checksum,
            )

            # 5. Generate and write QC artifacts
            qc_artifacts = self._generate_qc_artifacts(df_prepared, output_path)
            qc_checksums = self._checksum_calculator.compute_checksums(qc_artifacts)

            # 6. Build and write metadata
            meta = self._metadata_builder.build_run_metadata(
                run_context,
                final_result,
                qc_artifacts=qc_artifacts,
                qc_checksums=qc_checksums,
                qc_config=self._qc_config,
            )
            self.write_metadata(meta, output_path / "meta.yaml")

            return final_result

        except Exception as exc:
            self._record_write_error(entity_name, exc)
            raise

    def _stable_sort(
        self,
        df: pd.DataFrame,
        context: RunContext,
        column_order: list[str] | None = None,
    ) -> pd.DataFrame:
        """Apply deterministic sorting to DataFrame.

        Args:
            df: DataFrame to sort.
            context: Run context with config.
            column_order: Optional column order (skips column sorting if provided).

        Returns:
            Sorted DataFrame.
        """
        if not self._config.stable_sort:
            return df

        # 1. Sort columns (if no explicit order)
        if not column_order:
            df = df.reindex(sorted(df.columns), axis=1)

        # 2. Sort rows by business key if configured
        hashing_config = context.config.get("hashing", {})
        if isinstance(hashing_config, dict):
            keys = hashing_config.get("business_key_fields")
        else:
            keys = getattr(hashing_config, "business_key_fields", None)

        if keys:
            valid_keys = [k for k in keys if k in df.columns]
            if valid_keys:
                df = df.sort_values(by=valid_keys, ignore_index=True)

        return df

    def _generate_qc_artifacts(self, df: pd.DataFrame, output_path: Path) -> list[Path]:
        """Generate QC reports using the QC report generator.

        Args:
            df: Source DataFrame.
            output_path: Output directory.

        Returns:
            List of written QC artifact paths.
        """
        artifacts: list[Path] = []

        if self._qc_config.enable_quality_report:
            quality_report = self._qc_report_generator.build_quality_report(
                df, min_coverage=self._qc_config.min_coverage
            )
            path = self._qc_artifact_writer.write_qc_csv(
                quality_report, output_path / "quality_report_table.csv"
            )
            artifacts.append(path)

        if self._qc_config.enable_correlation_report:
            correlation_report = self._qc_report_generator.build_correlation_report(df)
            path = self._qc_artifact_writer.write_qc_csv(
                correlation_report, output_path / "correlation_report_table.csv"
            )
            artifacts.append(path)

        return artifacts

    def _record_write_error(self, entity_name: str, exc: Exception) -> None:
        """Record write error metric.

        Args:
            entity_name: Entity that failed.
            exc: Exception that occurred.
        """
        if not self._metrics:
            return

        self._metrics.inc_counter(
            MetricName.OUTPUT_WRITE_ERRORS_TOTAL,
            {"entity": entity_name, "error_type": exc.__class__.__name__},
        )


__all__ = ["UnifiedLoaderImpl"]
