"""
Unified output writer implementation.
"""

from pathlib import Path

import pandas as pd

from bioetl.domain.clients.base.output.contracts import (
    MetadataWriterABC,
    QualityReportABC,
    WriterABC,
    WriteResult,
)
from bioetl.domain.configs import DeterminismConfig, QcConfig
from bioetl.domain.models import RunContext
from bioetl.infrastructure.files.atomic import AtomicFileOperation
from bioetl.infrastructure.files.checksum import compute_file_sha256
from bioetl.infrastructure.output.column_order import apply_column_order
from bioetl.infrastructure.output.metadata import build_run_metadata


class UnifiedOutputWriter:
    """
    Фасад для записи результатов пайплайна.

    Обеспечивает:
    - Атомарную запись (write-temp-and-rename)
    - Генерацию meta.yaml
    - QC-отчеты (quality_report, correlation_report)
    """

    def __init__(
        self,
        writer: WriterABC,
        metadata_writer: MetadataWriterABC,
        quality_reporter: QualityReportABC,
        config: DeterminismConfig,
        qc_config: QcConfig | None = None,
        atomic_op: AtomicFileOperation | None = None,
    ) -> None:
        self._writer = writer
        self._metadata_writer = metadata_writer
        self._quality_reporter = quality_reporter
        self._config = config
        self._qc_config = qc_config or QcConfig()
        self._atomic_op = atomic_op or AtomicFileOperation()

    def write_result(
        self,
        df: pd.DataFrame,
        output_path: Path,
        entity_name: str,
        run_context: RunContext,
        *,
        column_order: list[str] | None = None,
    ) -> WriteResult:
        """Основной метод записи."""
        output_path.mkdir(parents=True, exist_ok=True)

        # 1. Валидация колонок (Check if strictly matches order if provided)
        # Note: Actual schema validation happens in PipelineBase.validate()
        # Here we ensure output structure and determinism.
        df_prepared = apply_column_order(df, column_order)

        # 2. Сортировка (Determinism)
        df_prepared = self._stable_sort(df_prepared, run_context, column_order)

        # 3. Атомарная запись
        data_path = output_path / f"{entity_name}.csv"

        # Wrapper to capture inner write result
        inner_result: WriteResult | None = None

        def write_wrapper(path: Path) -> None:
            nonlocal inner_result
            inner_result = self._writer.write(
                df_prepared, path, column_order=column_order
            )

        self._atomic_op.write_atomic(data_path, write_wrapper)

        if inner_result is None:
            raise RuntimeError("Inner writer did not return result")

        # 4. Вычисление checksum (после записи)
        checksum = compute_file_sha256(data_path)

        final_result = WriteResult(
            path=data_path,
            row_count=inner_result.row_count,
            duration_sec=inner_result.duration_sec,
            checksum=checksum,
        )

        qc_artifacts = self._generate_qc_artifacts(df_prepared, output_path)
        qc_checksums = {path.name: compute_file_sha256(path) for path in qc_artifacts}

        # 5. Запись метаданных
        meta = build_run_metadata(
            run_context,
            final_result,
            qc_artifacts=qc_artifacts,
            qc_checksums=qc_checksums,
            qc_config=self._qc_config,
        )
        self._metadata_writer.write_meta(meta, output_path / "meta.yaml")

        return final_result

    def _stable_sort(
        self,
        df: pd.DataFrame,
        context: RunContext,
        column_order: list[str] | None = None,
    ) -> pd.DataFrame:
        if not self._config.stable_sort:
            return df

        # 1. Sort columns
        if not column_order:
            df = df.reindex(sorted(df.columns), axis=1)

        # 2. Sort rows by business key if configured
        hashing_config = context.config.get("hashing", {})
        # Handle Pydantic model dump or dict
        if isinstance(hashing_config, dict):
            keys = hashing_config.get("business_key_fields")
        else:
            # Should be dict if model_dump() was used, but being safe
            keys = getattr(hashing_config, "business_key_fields", None)

        if keys:
            # Only sort by keys that exist in dataframe
            valid_keys = [k for k in keys if k in df.columns]
            if valid_keys:
                df = df.sort_values(by=valid_keys, ignore_index=True)

        return df

    def _generate_qc_artifacts(self, df: pd.DataFrame, output_path: Path) -> list[Path]:
        artifacts: list[Path] = []

        if self._qc_config.enable_quality_report:
            artifacts.append(
                self._write_qc_csv(
                    output_path / "quality_report_table.csv",
                    self._quality_reporter.build_quality_report(
                        df, min_coverage=self._qc_config.min_coverage
                    ),
                )
            )

        if self._qc_config.enable_correlation_report:
            artifacts.append(
                self._write_qc_csv(
                    output_path / "correlation_report_table.csv",
                    self._quality_reporter.build_correlation_report(df),
                )
            )

        return artifacts

    def _write_qc_csv(self, path: Path, df: pd.DataFrame) -> Path:
        def write_wrapper(temp_path: Path) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(temp_path, index=False)

        self._atomic_op.write_atomic(path, write_wrapper)
        return path
