"""
ChEMBL data extractor implementation.
"""

from typing import Any, Iterable

import pandas as pd

from bioetl.application.pipelines.contracts import ExtractorABC
from bioetl.domain.clients.base.logging.contracts import LoggerAdapterABC
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.record_source import ApiRecordSource, RecordSource
from bioetl.domain.transform.contracts import NormalizationServiceABC
from bioetl.infrastructure.files.csv_record_source import (
    CsvRecordSourceImpl,
    IdListRecordSourceImpl,
)


class ChemblExtractorImpl(ExtractorABC):
    """
    Extracts data from ChEMBL source (API or File) and applies normalization.
    """

    def __init__(
        self,
        config: PipelineConfig,
        extraction_service: ExtractionServiceABC,
        normalization_service: NormalizationServiceABC,
        logger: LoggerAdapterABC,
        record_source: RecordSource | None = None,
    ) -> None:
        self.config = config
        self.extraction_service = extraction_service
        self.normalization_service = normalization_service
        self.logger = logger
        self.record_source = record_source

    def extract(self, **kwargs: Any) -> Iterable[pd.DataFrame]:
        """
        Yields chunks of normalized data.
        """
        limit = kwargs.pop("limit", None)

        remaining = limit
        record_source = self.record_source or self._resolve_record_source(limit=limit)

        for raw_chunk in record_source.iter_records():
            if remaining is not None and remaining <= 0:
                break

            chunk_records = raw_chunk
            if remaining is not None:
                chunk_records = raw_chunk[:remaining]

            working_chunk = pd.DataFrame(chunk_records)

            normalized_chunk = self.normalization_service.normalize_batch(working_chunk)

            if not normalized_chunk.empty:
                yield normalized_chunk

            if remaining is not None:
                remaining -= len(chunk_records)
                if remaining <= 0:
                    break

    def _resolve_record_source(self, *, limit: int | None) -> RecordSource:
        """
        Builds record source based on current pipeline config.
        Falls back to API iteration when no input file is provided.
        """

        mode = getattr(self.config, "input_mode", "auto_detect")
        input_path = getattr(self.config, "input_path", None)
        csv_options = getattr(self.config, "csv_options", None)
        batch_size = getattr(self.config, "batch_size", None)

        if mode == "auto_detect" and input_path:
            mode = "csv"

        if mode == "csv":
            if not input_path:
                raise ValueError("input_path is required for CSV mode")
            return CsvRecordSourceImpl(
                input_path=input_path,
                csv_options=csv_options,
                limit=limit,
                chunk_size=batch_size,
                logger=self.logger,
            )

        if mode == "id_only":
            if not input_path:
                raise ValueError("input_path is required for ID-only mode")
            id_column = self._resolve_primary_key()
            filter_key = f"{id_column}__in"
            source_config = self.config.get_source_config(self.config.provider)
            return IdListRecordSourceImpl(
                input_path=input_path,
                id_column=id_column,
                csv_options=csv_options,
                limit=limit,
                extraction_service=self.extraction_service,
                source_config=source_config,
                entity=self.config.entity_name,
                filter_key=filter_key,
                logger=self.logger,
                chunk_size=batch_size,
            )

        filters = dict(getattr(self.config, "pipeline", {}) or {})
        if limit is not None:
            filters["limit"] = limit

        return ApiRecordSource(
            extraction_service=self.extraction_service,
            entity=self.config.entity_name,
            filters=filters,
            chunk_size=batch_size,
        )

    def _resolve_primary_key(self) -> str:
        pk = getattr(self.config, "primary_key", None)
        pipeline_cfg = getattr(self.config, "pipeline", {}) or {}
        if not pk and "primary_key" in pipeline_cfg:
            pk = pipeline_cfg["primary_key"]
        if not pk:
            pk = f"{self.config.entity_name}_id"
        if not pk:
            raise ValueError(
                f"Could not resolve ID column for entity '{self.config.entity_name}'"
            )
        return pk
