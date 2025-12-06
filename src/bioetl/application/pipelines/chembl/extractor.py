"""
ChEMBL data extractor implementation.
"""
from typing import Any, Iterable, cast
from pathlib import Path

import pandas as pd

from bioetl.application.pipelines.contracts import ExtractorABC
from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.normalization_service import NormalizationService
from bioetl.domain.record_source import ApiRecordSource, RecordSource
from bioetl.application.config.pipeline_config_schema import PipelineConfig
from bioetl.infrastructure.config.models import ChemblSourceConfig
from bioetl.infrastructure.files.csv_record_source import (
    CsvRecordSourceImpl,
    IdListRecordSourceImpl,
)
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC


class ChemblExtractorImpl(ExtractorABC):
    """
    Extracts data from ChEMBL source (API or File) and applies normalization.
    """

    def __init__(
        self,
        config: PipelineConfig,
        extraction_service: ExtractionServiceABC,
        normalization_service: NormalizationService,
        logger: LoggerAdapterABC,
        record_source: RecordSource | None = None,
    ) -> None:
        self.config = config
        self.extraction_service = extraction_service
        self.normalization_service = normalization_service
        self.logger = logger
        self.record_source = record_source or ApiRecordSource(
            extraction_service=extraction_service,
            entity=config.entity_name,
            filters=config.pipeline,
        )

    def extract(self, **kwargs: Any) -> Iterable[pd.DataFrame]:
        """
        Yields chunks of normalized data.
        """
        limit = kwargs.pop("limit", None)
        record_source = self._resolve_record_source(limit)

        remaining = limit
        for raw_chunk in record_source.iter_records():
            working_chunk = raw_chunk
            if remaining is not None:
                if remaining <= 0:
                    break
                working_chunk = raw_chunk.head(remaining)

            normalized_chunk = self.normalization_service.normalize_batch(
                working_chunk
            )

            if not normalized_chunk.empty:
                yield normalized_chunk

            if remaining is not None:
                remaining -= len(working_chunk)
                if remaining <= 0:
                    break

    def _resolve_record_source(self, limit: int | None) -> RecordSource:
        """Возвращает источник записей с учетом конфигурации input_mode."""

        if hasattr(self.config, "input_mode") and hasattr(self.config, "input_path"):
            mode = self.config.input_mode
            path = self.config.input_path

            if mode == "csv" and path:
                return CsvRecordSourceImpl(
                    input_path=Path(path),
                    csv_options=self.config.csv_options,
                    limit=limit,
                    logger=self.logger,
                )
            if mode == "id_only" and path:
                source_config = self.config.get_source_config(self.config.provider)
                id_column = self.config.primary_key or f"{self.config.entity_name}_id"
                filter_key = f"{id_column}__in"
                return IdListRecordSourceImpl(
                    input_path=Path(path),
                    id_column=id_column,
                    csv_options=self.config.csv_options,
                    limit=limit,
                    extraction_service=self.extraction_service,
                    source_config=cast(ChemblSourceConfig, source_config),
                    entity=self.config.entity_name,
                    filter_key=filter_key,
                    logger=self.logger,
                )

        return self.record_source

