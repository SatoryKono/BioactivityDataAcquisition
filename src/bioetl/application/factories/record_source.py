"""
Factory for creating RecordSource instances.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable

from bioetl.application.files.csv_record_source import (
    CsvRecordSourceImpl,
    IdListRecordSourceImpl,
)
from bioetl.application.helpers import resolve_primary_key
from bioetl.application.sources import ApiRecordSource
from bioetl.application.transform.pandas_batch_adapter import PandasBatchAdapter
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.providers import ProviderDefinition
from bioetl.domain.record_source import RecordSourceABC


class RecordSourceFactoryABC(ABC):
    """Abstract factory for creating record sources.

    Defines the contract for factories that create RecordSourceABC instances
    based on pipeline input configuration (CSV, ID-only, or API mode).
    """

    @abstractmethod
    def create_record_source(
        self,
        extraction_service: Any,
        *,
        limit: int | None = None,
        logger: LoggingPortABC,
        model_cls: type | None = None,
        batch_adapter: Callable[..., Any] | None = None,
    ) -> RecordSourceABC:
        """Create record source based on pipeline input configuration.

        Args:
            extraction_service: Service for API extraction.
            limit: Maximum number of records to fetch.
            logger: Logger instance.
            model_cls: Optional Pydantic model class for CSV parsing.
            batch_adapter: Optional batch processing callable for API mode.

        Returns:
            Configured RecordSourceABC instance.
        """


class RecordSourceFactory(RecordSourceFactoryABC):
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
        model_cls: type | None = None,
        batch_adapter: Callable[..., Any] | None = None,
    ) -> RecordSourceABC:
        """Create record source based on pipeline input configuration.

        Args:
            extraction_service: Service for API extraction.
            limit: Maximum number of records to fetch.
            logger: Logger instance.
            model_cls: Optional Pydantic model class for CSV parsing.
            batch_adapter: Optional batch processing callable for API mode.
                If not provided, creates a default PandasBatchAdapter.

        Returns:
            Configured RecordSourceABC instance.
        """
        mode = self._config.source.input_mode
        path = self._config.source.input_path
        chunk_size = self._config.source.batch_size

        if mode == "auto_detect" and path:
            mode = "csv"

        if mode == "csv":
            if path is None:
                raise ValueError("input_path is required for CSV mode")
            return CsvRecordSourceImpl(
                input_path=Path(path),
                csv_options=self._config.source.csv,
                limit=limit,
                logger=logger,
                chunk_size=chunk_size,
                model_cls=model_cls,
            )

        if mode == "id_only":
            if path is None:
                raise ValueError("input_path is required for ID-only mode")

            source_config = self._resolve_provider_config(self._provider_definition)
            id_column = resolve_primary_key(self._config)
            filter_key = f"{id_column}__in"
            return IdListRecordSourceImpl(
                input_path=Path(path),
                id_column=id_column,
                csv_options=self._config.source.csv,
                limit=limit,
                extraction_service=extraction_service,
                source_config=source_config,
                entity=self._config.entity_name,
                filter_key=filter_key,
                logger=logger,
                chunk_size=chunk_size,
            )

        # API filters - stages are not filters, use empty dict for API mode
        filters: dict[str, Any] = {}
        if limit is not None:
            filters["limit"] = limit

        resolved_batch_adapter = batch_adapter
        if resolved_batch_adapter is None:
            resolved_batch_adapter = PandasBatchAdapter(
                model_cls=model_cls
            ).process_batch

        return ApiRecordSource(
            extraction_service=extraction_service,
            entity=self._config.entity_name,
            filters=filters,
            chunk_size=chunk_size,
            batch_adapter=resolved_batch_adapter,
        )
