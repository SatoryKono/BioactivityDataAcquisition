"""
Base pipeline implementation for ChEMBL data extraction.
"""
from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any

import pandas as pd

from bioetl.application.pipelines.base import PipelineBase
from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.models import RunContext
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.transform.impl.normalize import NormalizationService
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.config.models import (
    ChemblSourceConfig,
    CsvInputOptions,
    PipelineConfig,
)
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


def _chunk_list(data: list[Any], size: int) -> Iterator[list[Any]]:
    """Yield successive chunks from data."""
    for i in range(0, len(data), size):
        yield data[i:i + size]


class RecordSource(ABC):
    """Абстракция источника записей."""

    @abstractmethod
    def load(self) -> pd.DataFrame:
        """Загружает DataFrame из источника."""


class ApiRecordSource(RecordSource):
    def __init__(
        self,
        extraction_service: ExtractionServiceABC,
        entity: str,
        filters: dict[str, Any],
        logger: LoggerAdapterABC,
    ) -> None:
        self._extraction_service = extraction_service
        self._entity = entity
        self._filters = filters
        self._logger = logger

    def load(self) -> pd.DataFrame:
        self._logger.info(f"Extracting {self._entity} from API...")
        return self._extraction_service.extract_all(
            self._entity, **self._filters
        )


class CsvDatasetRecordSource(RecordSource):
    def __init__(
        self,
        path: str,
        csv_options: CsvInputOptions,
        limit: int | None,
        logger: LoggerAdapterABC,
    ) -> None:
        self._path = path
        self._csv_options = csv_options
        self._limit = limit
        self._logger = logger

    def load(self) -> pd.DataFrame:
        self._logger.info(f"Extracting records from CSV dataset: {self._path}")
        header = 0 if self._csv_options.header else None
        df = pd.read_csv(
            self._path,
            delimiter=self._csv_options.delimiter,
            header=header,
        )
        if self._limit is not None:
            df = df.head(self._limit)
        return df


class CsvIdOnlyRecordSource(RecordSource):
    def __init__(
        self,
        path: str,
        id_column: str,
        csv_options: CsvInputOptions,
        limit: int | None,
        extraction_service: ExtractionServiceABC,
        source_config: ChemblSourceConfig,
        entity: str,
        filter_key: str,
        logger: LoggerAdapterABC,
    ) -> None:
        self._path = path
        self._id_column = id_column
        self._csv_options = csv_options
        self._limit = limit
        self._extraction_service = extraction_service
        self._source_config = source_config
        self._entity = entity
        self._filter_key = filter_key
        self._logger = logger

    def load(self) -> pd.DataFrame:
        if not self._id_column:
            raise ValueError("ID_COLUMN must be defined for ID-only mode")
        if not self._filter_key:
            raise ValueError("API_FILTER_KEY must be defined for ID-only mode")

        header = 0 if self._csv_options.header else None
        usecols = [self._id_column] if self._csv_options.header else [0]
        names = [self._id_column] if not self._csv_options.header else None

        df_ids = pd.read_csv(
            self._path,
            delimiter=self._csv_options.delimiter,
            usecols=usecols,
            header=header,
            names=names,
        )

        ids = df_ids[self._id_column].dropna().astype(str).tolist()
        if self._limit is not None:
            ids = ids[: self._limit]

        if not ids:
            return pd.DataFrame()

        batch_size = self._source_config.resolve_effective_batch_size(
            limit=self._limit, hard_cap=25
        )

        records: list[dict[str, Any]] = []

        for batch_ids in _chunk_list(ids, batch_size):
            response = self._extraction_service.request_batch(
                self._entity, batch_ids, self._filter_key
            )
            batch_records = self._extraction_service.parse_response(response)
            serialized_records = self._extraction_service.serialize_records(
                self._entity, batch_records
            )
            records.extend(serialized_records)

        return pd.DataFrame(records)


class ChemblPipelineBase(PipelineBase):
    """
    Базовый класс для ChEMBL-пайплайнов.

    Расширяет PipelineBase функциональностью:
    - Определение версии релиза ChEMBL
    - Интеграция с ChemblExtractionService
    - Generic extract с поддержкой CSV input
    - Хуки pre_transform
    - Нормализация полей (NormalizationService)
    """

    # Entity-specific config (override in subclasses)
    ID_COLUMN: str = ""  # e.g. "activity_id", "assay_chembl_id"
    API_FILTER_KEY: str = ""  # e.g. "activity_id__in", "assay_chembl_id__in"

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggerAdapterABC,
        validation_service: ValidationService,
        output_writer: UnifiedOutputWriter,
        extraction_service: ExtractionServiceABC,
        hash_service: HashService | None = None,
    ) -> None:
        super().__init__(
            config,
            logger,
            validation_service,
            output_writer,
            hash_service,
        )
        self._extraction_service = extraction_service
        self._chembl_release: str | None = None

        # Initialize normalization service
        self._normalization_service = NormalizationService(config)

    def get_version(self) -> str:
        """Возвращает версию релиза ChEMBL (например, 'chembl_34')."""
        if self._chembl_release is None:
            self._chembl_release = (
                self._extraction_service.get_release_version()
            )
        return self._chembl_release
    
    # Alias for compatibility if needed elsewhere, but we use get_version now.
    def get_chembl_release(self) -> str:
        return self.get_version()

    def _resolve_source_config(self) -> ChemblSourceConfig:
        """Resolve and validate ChEMBL source configuration."""
        config = self._config.provider_config
        if not isinstance(config, ChemblSourceConfig):
            raise TypeError("Expected ChemblSourceConfig")
        return config

    def extract(self, **kwargs: Any) -> pd.DataFrame:
        """
        Generic extract with explicit record source selection.

        Record source resolution:
        - input_mode=csv: read rows from CSV using csv_options
        - input_mode=id_only: read IDs from CSV and fetch records from API
        - input_mode=auto_detect: API if no input_path, CSV dataset otherwise
        """
        limit = kwargs.pop("limit", None)
        record_source = self._build_record_source(
            limit=limit, extract_kwargs=kwargs
        )
        return record_source.load()

    def _build_record_source(
        self, *, limit: int | None, extract_kwargs: dict[str, Any]
    ) -> RecordSource:
        filters = self._config.pipeline.copy()
        filters.update(extract_kwargs)
        if limit is not None:
            filters["limit"] = limit

        mode = self._config.input_mode
        path = self._config.input_path
        if mode == "auto_detect" and path:
            mode = "csv"

        if mode == "csv":
            if path is None:
                raise ValueError("input_path is required for CSV mode")
            return CsvDatasetRecordSource(
                path=path,
                csv_options=self._config.csv_options,
                limit=limit,
                logger=self._logger,
            )

        if mode == "id_only":
            if path is None:
                raise ValueError("input_path is required for ID-only mode")
            source_config = self._resolve_source_config()
            return CsvIdOnlyRecordSource(
                path=path,
                id_column=self.ID_COLUMN,
                csv_options=self._config.csv_options,
                limit=limit,
                extraction_service=self._extraction_service,
                source_config=source_config,
                entity=self._config.entity_name,
                filter_key=self.API_FILTER_KEY,
                logger=self._logger,
            )

        return ApiRecordSource(
            extraction_service=self._extraction_service,
            entity=self._config.entity_name,
            filters=filters,
            logger=self._logger,
        )

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Цепочка трансформаций для ChEMBL:
        pre_transform → _do_transform → normalize_fields → enforce_schema
        """
        df = self.pre_transform(df)
        df = self._do_transform(df)

        # Выполняем нормализацию (строки, числа, вложенные структуры)
        df = self._normalization_service.normalize_fields(df)

        # Приводим к схеме (добавляем отсутствующие колонки, упорядочиваем)
        df = self._enforce_schema(df)

        # Удаляем строки с NULL в обязательных колонках
        df = self._drop_nulls_in_required_columns(df)

        return df

    def _drop_nulls_in_required_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Удаляет строки, где обязательные (non-nullable) колонки содержат NULL.
        Игнорирует генерируемые колонки (hash_row, hash_business_key),
        так как они вычисляются позже.
        """
        entity = self._config.entity_name
        schema_cls = self._validation_service.get_schema(entity)
        schema = schema_cls.to_schema()

        # Columns to ignore during this check because they are generated later
        ignored_cols = {"hash_row", "hash_business_key", "index", "database_version", "extracted_at"}

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
        entity = self._config.entity_name
        schema_columns = self._validation_service.get_schema_columns(entity)

        for col in schema_columns:
            if col not in df.columns:
                df[col] = None

        return df[schema_columns]

    def _enrich_context(self, context: RunContext) -> None:
        """Добавляет chembl_release в метаданные контекста."""
        context.metadata["chembl_release"] = self.get_version()
