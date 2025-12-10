"""
Factory for creating RecordSource instances.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bioetl.application.files.csv_record_source import (
    CsvRecordSourceImpl,
    IdListRecordSourceImpl,
)
from bioetl.application.transform.pandas_batch_adapter import PandasBatchAdapter
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.providers import ProviderDefinition
from bioetl.application.sources import ApiRecordSource
from bioetl.domain.record_source import RecordSourceABC


class RecordSourceFactory:
    """Factory for creating record sources."""

    def __init__(
        self,
        config: PipelineConfig,
        provider_definition: ProviderDefinition,
        resolve_provider_config: Any,
    ) -> None:
        self._config = config
        self._provider_definition = provider_definition
        self._resolve_provider_config = resolve_provider_config

    def create_record_source(
        self,
        extraction_service: Any,
        *,
        limit: int | None = None,
        logger: LoggingPortABC,
    ) -> RecordSourceABC:
        """Create record source based on pipeline input configuration."""
        mode = self._config.input_mode
        path = self._config.input_path

        if mode == "auto_detect" and path:
            mode = "csv"

        if mode == "csv":
            if path is None:
                raise ValueError("input_path is required for CSV mode")
            return CsvRecordSourceImpl(
                input_path=Path(path),
                csv_options=self._config.csv_options,
                limit=limit,
                logger=logger,
                chunk_size=None,
            )

        if mode == "id_only":
            if path is None:
                raise ValueError("input_path is required for ID-only mode")

            source_config = self._resolve_provider_config(self._provider_definition)
            id_column = self._resolve_primary_key()
            filter_key = f"{id_column}__in"
            return IdListRecordSourceImpl(
                input_path=Path(path),
                id_column=id_column,
                csv_options=self._config.csv_options,
                limit=limit,
                extraction_service=extraction_service,
                source_config=source_config,
                entity=self._config.entity_name,
                filter_key=filter_key,
                logger=logger,
                chunk_size=None,
            )

        filters = self._config.pipeline.copy()
        if limit is not None:
            filters["limit"] = limit

        return ApiRecordSource(
            extraction_service=extraction_service,
            entity=self._config.entity_name,
            filters=filters,
            chunk_size=self._config.batch_size,
            batch_adapter=PandasBatchAdapter().process_batch,
        )

    def _resolve_primary_key(self) -> str:
        pk = self._config.primary_key
        if not pk and self._config.pipeline and "primary_key" in self._config.pipeline:
            pk = self._config.pipeline["primary_key"]
        if not pk:
            pk = f"{self._config.entity_name}_id"
        if not pk:
            raise ValueError(
                f"Could not resolve primary key for entity '{self._config.entity_name}'"
            )
        return pk
