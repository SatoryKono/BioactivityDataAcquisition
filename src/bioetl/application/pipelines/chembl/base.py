"""
Base pipeline implementation for ChEMBL data extraction.
"""
from collections.abc import Iterator
from typing import Any

import pandas as pd

from bioetl.application.pipelines.base import PipelineBase
from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.ingestion.contracts import IngestionServiceABC
from bioetl.domain.models import RunContext
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.config.models import (
    ChemblSourceConfig,
    PipelineConfig,
)
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


def _chunk_list(data: list[Any], size: int) -> Iterator[list[Any]]:
    """Yield successive chunks from data."""
    for i in range(0, len(data), size):
        yield data[i:i + size]


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
        ingestion_service: IngestionServiceABC,
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
        self._ingestion_service = ingestion_service

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
        config = self._config.get_source_config("chembl")
        if not isinstance(config, ChemblSourceConfig):
            raise TypeError("Expected ChemblSourceConfig")
        return config

    def extract(self, **kwargs: Any) -> pd.DataFrame:
        """
        Generic extract with CSV input support.

        If config.cli['input_file'] is provided:
        - Full CSV data → returned as-is (with optional limit)
        - ID-only CSV → fetches full records from API

        Otherwise delegates to ChemblExtractionService.extract_all().
        """
        entity = self._config.entity_name
        limit = kwargs.get("limit")
        path = self._config.cli.get("input_file")

        if path:
            self._logger.info(f"Extracting {entity} from CSV: {path}")
            return self._extract_from_csv(path, limit)

        self._logger.info(f"Extracting {entity} from API...")
        filters = self._config.pipeline.copy()
        filters.update(kwargs)
        return self._extraction_service.extract_all(entity, **filters)

    def _extract_from_csv(
        self, path: str, limit: int | None
    ) -> pd.DataFrame:
        """Handle CSV input (full data or ID-only)."""
        id_col = self.ID_COLUMN
        if not id_col:
            raise ValueError(
                f"{self.__class__.__name__} must define ID_COLUMN"
            )

        header = pd.read_csv(path, nrows=0)
        if id_col not in header.columns:
            raise ValueError(f"Input file {path} must contain '{id_col}'")

        # Check for explicit config override
        is_full_dataset = self._config.cli.get("input_full_dataset")

        if is_full_dataset is None:
            # Heuristic: <= 2 columns means it's likely just IDs
            is_id_only = len(header.columns) <= 2
            is_full_dataset = not is_id_only

        if is_full_dataset:
            self._logger.info("Using input CSV as full dataset")
            df = pd.read_csv(path)
            if limit:
                df = df.head(limit)
            return df

        self._logger.info("Detected ID-only CSV, fetching from API...")
        return self._fetch_by_ids(path, id_col, limit)

    def _fetch_by_ids(
        self, path: str, id_col: str, limit: int | None
    ) -> pd.DataFrame:
        """Fetch full records from API for IDs in CSV."""
        df_ids = pd.read_csv(path, usecols=[id_col])
        ids = df_ids[id_col].dropna().astype(str).tolist()

        if limit:
            ids = ids[:limit]

        if not ids:
            return pd.DataFrame()

        source_config = self._resolve_source_config()
        batch_size = source_config.resolve_effective_batch_size(
            limit=limit, hard_cap=25
        )

        records: list[dict[str, Any]] = []
        entity = self._config.entity_name

        for batch_ids in _chunk_list(ids, batch_size):
            response = self._request_batch(entity, batch_ids)
            batch_records = self._extraction_service.parse_response(response)
            # Serialize records using model to ensure format consistency (flattening, etc)
            serialized_records = self._extraction_service.serialize_records(entity, batch_records)
            records.extend(serialized_records)

        return pd.DataFrame(records)

    def _request_batch(
        self, entity: str, batch_ids: list[str]
    ) -> dict[str, Any]:
        """Request a batch of records by IDs from the API."""
        filter_key = self.API_FILTER_KEY
        if not filter_key:
            raise ValueError(
                f"{self.__class__.__name__} must define API_FILTER_KEY"
            )
        return self._extraction_service.request_batch(
            entity, batch_ids, filter_key
        )

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Цепочка трансформаций для ChEMBL:
        pre_transform → _do_transform → normalize_fields → enforce_schema
        """
        df = self.pre_transform(df)
        df = self._do_transform(df)

        return self._ingestion_service.ingest(
            df,
            entity_name=self._config.entity_name,
        )

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

    def _enrich_context(self, context: RunContext) -> None:
        """Добавляет chembl_release в метаданные контекста."""
        context.metadata["chembl_release"] = self.get_version()
