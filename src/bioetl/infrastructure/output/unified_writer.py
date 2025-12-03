"""
Unified output writer implementation.
"""
from pathlib import Path

import pandas as pd

from bioetl.domain.models import RunContext
from bioetl.domain.validation import SchemaProviderABC
from bioetl.infrastructure.config.models import DeterminismConfig
from bioetl.infrastructure.files.atomic import AtomicFileOperation
from bioetl.infrastructure.files.checksum import compute_file_sha256
from bioetl.infrastructure.output.contracts import (
    MetadataWriterABC,
    WriterABC,
    WriteResult,
)
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
        config: DeterminismConfig,
        schema_provider: SchemaProviderABC | None = None,
        atomic_op: AtomicFileOperation | None = None,
    ) -> None:
        self._writer = writer
        self._metadata_writer = metadata_writer
        self._config = config
        self._schema_provider = schema_provider
        self._atomic_op = atomic_op or AtomicFileOperation()

    def write_result(
        self,
        df: pd.DataFrame,
        output_path: Path,
        entity_name: str,
        run_context: RunContext,
    ) -> WriteResult:
        """Основной метод записи."""
        output_path.mkdir(parents=True, exist_ok=True)

        # 1. Сортировка
        df = self._stable_sort(df, run_context)

        # 2. Атомарная запись
        data_path = output_path / f"{entity_name}.csv"

        # Wrapper to capture inner write result
        inner_result: WriteResult | None = None

        def write_wrapper(path: Path) -> None:
            nonlocal inner_result
            inner_result = self._writer.write(df, path)

        self._atomic_op.write_atomic(data_path, write_wrapper)

        if inner_result is None:
            raise RuntimeError("Inner writer did not return result")

        # 3. Вычисление checksum (после записи)
        checksum = compute_file_sha256(data_path)

        final_result = WriteResult(
            path=data_path,
            row_count=inner_result.row_count,
            duration_sec=inner_result.duration_sec,
            checksum=checksum,
        )

        # 4. Запись метаданных
        meta = build_run_metadata(run_context, final_result)
        self._metadata_writer.write_meta(meta, output_path / "meta.yaml")

        # 5. QC-отчеты (placeholder for future implementation)
        # Previous code had omitted QC generation comment.

        return final_result

    def _stable_sort(
        self, df: pd.DataFrame, context: RunContext
    ) -> pd.DataFrame:
        if not self._config.stable_sort:
            return df

        df, schema_applied = self._apply_output_schema(df, context)
        if not schema_applied:
            df = df.reindex(sorted(df.columns), axis=1)

        # Sort rows by business key if configured
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

    def _apply_output_schema(
        self, df: pd.DataFrame, context: RunContext
    ) -> tuple[pd.DataFrame, bool]:
        descriptor = None
        if self._schema_provider:
            descriptor = self._schema_provider.get_output_descriptor(
                context.entity_name
            )

        if descriptor is None:
            return df, False

        missing_columns = [
            column for column in descriptor.column_order if column not in df.columns
        ]
        if missing_columns:
            missing_str = ", ".join(sorted(missing_columns))
            raise ValueError(
                "Missing required columns for output schema "
                f"'{context.entity_name}': {missing_str}"
            )

        ordered_df = df.loc[:, descriptor.column_order]
        return ordered_df, True
