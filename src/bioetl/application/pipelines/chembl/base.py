"""Base pipeline implementation for ChEMBL data extraction."""
from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pandas as pd

from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.hooks import ErrorPolicyABC, PipelineHookABC
from bioetl.clients.csv_record_source import CsvRecordSource, IdListRecordSource
from bioetl.domain.normalization_service import ChemblNormalizationService, NormalizationService
from bioetl.domain.record_source import ApiRecordSource, RecordSource
from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.models import RunContext
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.config.models import ChemblSourceConfig, PipelineConfig
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


class ChemblPipelineBase(PipelineBase):
    """Базовый класс для ChEMBL-пайплайнов."""

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggerAdapterABC,
        validation_service: ValidationService,
        output_writer: UnifiedOutputWriter,
        extraction_service: ExtractionServiceABC,
        record_source: RecordSource | None = None,
        normalization_service: NormalizationService | None = None,
        hash_service: HashService | None = None,
        hooks: list[PipelineHookABC] | None = None,
        error_policy: ErrorPolicyABC | None = None,
    ) -> None:
        super().__init__(
            config,
            logger,
            validation_service,
            output_writer,
            hash_service,
            hooks,
            error_policy,
        )
        self._extraction_service = extraction_service
        self._record_source = record_source or ApiRecordSource(
            extraction_service=extraction_service,
            entity=config.entity_name,
            filters=config.pipeline,
        )
        self._normalization_service = normalization_service or ChemblNormalizationService(
            config
        )
        self._chembl_release: str | None = None

    def get_version(self) -> str:
        """Возвращает версию релиза ChEMBL (например, 'chembl_34')."""
        if self._chembl_release is None:
            self._chembl_release = (
                self._extraction_service.get_release_version()
            )
        return self._chembl_release

    def extract(self, **kwargs: Any) -> pd.DataFrame:
        """Извлекает данные через RecordSource и нормализует записи."""
        limit = kwargs.pop("limit", None)
        
        # Recreate record_source if input_mode or input_path changed
        # This allows tests to change config after pipeline creation
        record_source = self._record_source
        if hasattr(self._config, 'input_mode') and hasattr(self._config, 'input_path'):
            mode = self._config.input_mode
            path = self._config.input_path
            
            if mode == "csv" and path:
                record_source = CsvRecordSource(
                    input_path=Path(path),
                    csv_options=self._config.csv_options,
                    limit=limit,
                    logger=self._logger,
                )
            elif mode == "id_only" and path:
                source_config = self._config.get_source_config(self._config.provider)
                id_column = self._config.primary_key or f"{self._config.entity_name}_id"
                filter_key = f"{id_column}__in"
                record_source = IdListRecordSource(
                    input_path=Path(path),
                    id_column=id_column,
                    csv_options=self._config.csv_options,
                    limit=limit,
                    extraction_service=self._extraction_service,
                    source_config=cast(ChemblSourceConfig, source_config),
                    entity=self._config.entity_name,
                    filter_key=filter_key,
                    logger=self._logger,
                )
        
        remaining = limit
        normalized_chunks: list[pd.DataFrame] = []

        for raw_chunk in record_source.iter_records():
            if raw_chunk.empty:
                continue

            working_chunk = raw_chunk
            if remaining is not None:
                if remaining <= 0:
                    break
                working_chunk = raw_chunk.head(remaining)
                remaining -= len(working_chunk)

            normalized_chunk = self._normalization_service.normalize_batch(
                working_chunk
            )
            normalized_chunks.append(normalized_chunk)

            if remaining is not None and remaining <= 0:
                break

        if not normalized_chunks:
            return pd.DataFrame()

        return pd.concat(normalized_chunks, ignore_index=True)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Цепочка трансформаций для ChEMBL:
        pre_transform → _do_transform → normalize → enforce_schema → drop nulls
        """
        df = self.pre_transform(df)
        df = self._do_transform(df)
        df = self._normalization_service.normalize_dataframe(df)

        df = self._enforce_schema(df)
        df = self._drop_nulls_in_required_columns(df)

        return df

    def _drop_nulls_in_required_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Удаляет строки, где обязательные (non-nullable) колонки содержат NULL.
        Игнорирует генерируемые колонки (hash_row, hash_business_key),
        так как они вычисляются позже.
        """
        schema_name = self._schema_contract.schema_out
        schema_cls = self._validation_service.get_schema(schema_name)
        schema = schema_cls.to_schema()

        ignored_cols = {
            "hash_row",
            "hash_business_key",
            "index",
            "database_version",
            "extracted_at",
        }

        required_cols = [
            name
            for name, col in schema.columns.items()
            if not col.nullable
            and name in df.columns
            and name not in ignored_cols
        ]

        if not required_cols:
            return df

        initial_count = len(df)
        df_clean = df.dropna(subset=required_cols)
        dropped_count = initial_count - len(df_clean)

        if dropped_count > 0:
            self._logger.warning(
                f"Dropped {dropped_count} rows with nulls in required columns: {required_cols}"
            )

        return df_clean

    def pre_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Хук для предварительной обработки (можно переопределить)."""
        return df

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Основная логика трансформации.
        По умолчанию возвращает DataFrame как есть.
        Наследники могут переопределить или расширить.
        """
        return df

    def _enforce_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Приводит DataFrame к схеме: заполняет отсутствующие колонки None,
        оставляет только колонки из схемы в правильном порядке.
        """
        schema_name = self._schema_contract.schema_out
        schema_columns = self._validation_service.get_schema_columns(schema_name)

        for col in schema_columns:
            if col not in df.columns:
                df[col] = None

        return df[schema_columns]

    def _enrich_context(self, context: RunContext) -> None:
        """Добавляет chembl_release в метаданные контекста."""
        context.metadata["chembl_release"] = self.get_version()

    def get_chembl_release(self) -> str:
        """Alias for get_version for backward compatibility."""
        return self.get_version()
