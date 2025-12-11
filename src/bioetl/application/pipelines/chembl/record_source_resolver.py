"""Record source resolution for ChEMBL pipelines.

This module provides the RecordSourceResolver class that handles
determination and creation of the appropriate record source based
on pipeline configuration.

Extracted from ChemblPipelineBase to reduce class size and improve
testability of record source resolution logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.files.csv_record_source import (
    CsvRecordSourceImpl,
    IdListRecordSourceImpl,
)
from bioetl.domain.configs import ChemblSourceConfig
from bioetl.domain.record_source import RecordSourceABC

if TYPE_CHECKING:
    from bioetl.domain.configs import PipelineConfig
    from bioetl.domain.observability import LoggingPortABC
    from bioetl.domain.ports.extraction import ExtractionServiceABC


class RecordSourceResolver:
    """Resolves and creates appropriate record source for ChEMBL pipelines.

    This class encapsulates the logic for determining which record source
    to use based on the pipeline configuration's input mode.

    Supported modes:
        - csv: Read records from a CSV file
        - id_only: Read IDs from file and fetch records from API
        - auto_detect: Automatically determine mode based on input_path
        - api (default): Fetch records directly from ChEMBL API
    """

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggingPortABC,
        extraction_service: ExtractionServiceABC,
        id_column: str,
        filter_key: str,
    ) -> None:
        """Initialize record source resolver.

        Args:
            config: Pipeline configuration.
            logger: Logger for diagnostic messages.
            extraction_service: Service for API-based extraction.
            id_column: Column name for record IDs.
            filter_key: API filter key for ID-based queries.
        """
        self._config = config
        self._logger = logger
        self._extraction_service = extraction_service
        self._id_column = id_column
        self._filter_key = filter_key

    def resolve(self) -> RecordSourceABC | None:
        """Resolve and create the appropriate record source.

        Returns:
            RecordSourceABC instance for file-based modes, or None for API mode.

        Raises:
            ValueError: If required configuration is missing.
            TypeError: If provider config type is invalid.
        """
        source_cfg = self._config.source
        mode = self._resolve_effective_mode(source_cfg)

        if mode == "csv":
            return self._create_csv_source(source_cfg)
        elif mode == "id_only":
            return self._create_id_list_source(source_cfg)

        # API mode - no file-based record source needed
        return None

    def _resolve_effective_mode(self, source_cfg: "DataSourceConfig") -> str:  # type: ignore[name-defined]
        """Determine effective input mode from configuration.

        Args:
            source_cfg: Source configuration section.

        Returns:
            Effective input mode string.
        """
        mode = source_cfg.input_mode

        # Auto-detect based on input_path presence
        if mode == "auto_detect" and source_cfg.input_path:
            return "csv"

        return mode or "api"

    def _create_csv_source(
        self, source_cfg: "DataSourceConfig"  # type: ignore[name-defined]
    ) -> CsvRecordSourceImpl:
        """Create CSV record source.

        Args:
            source_cfg: Source configuration.

        Returns:
            CsvRecordSourceImpl instance.

        Raises:
            ValueError: If input_path is not configured.
        """
        input_path = source_cfg.input_path
        if input_path is None:
            raise ValueError("input_path is required when input_mode is 'csv'.")

        return CsvRecordSourceImpl(
            input_path=Path(input_path),
            csv_options=source_cfg.csv,
            limit=None,
            logger=self._logger,
            chunk_size=source_cfg.batch_size,
        )

    def _create_id_list_source(
        self, source_cfg: "DataSourceConfig"  # type: ignore[name-defined]
    ) -> IdListRecordSourceImpl:
        """Create ID list record source.

        Args:
            source_cfg: Source configuration.

        Returns:
            IdListRecordSourceImpl instance.

        Raises:
            ValueError: If input_path is not configured.
            TypeError: If provider config is not ChemblSourceConfig.
        """
        input_path = source_cfg.input_path
        if input_path is None:
            raise ValueError("input_path is required when input_mode is 'id_only'.")

        provider_cfg = self._config.get_source_config(self._config.provider)

        if not isinstance(provider_cfg, ChemblSourceConfig):
            raise TypeError(
                "ChemblSourceConfig is required for id_only input_mode."
            )

        return IdListRecordSourceImpl(
            input_path=Path(input_path),
            id_column=self._id_column,
            csv_options=source_cfg.csv,
            limit=None,
            extraction_service=self._extraction_service,
            source_config=provider_cfg,
            entity=self._config.entity_name,
            filter_key=self._filter_key,
            logger=self._logger,
            chunk_size=source_cfg.batch_size,
        )


def resolve_record_source(
    config: PipelineConfig,
    logger: LoggingPortABC,
    extraction_service: ExtractionServiceABC,
    id_column: str,
    filter_key: str,
) -> RecordSourceABC | None:
    """Convenience function to resolve record source.

    Args:
        config: Pipeline configuration.
        logger: Logger instance.
        extraction_service: Extraction service.
        id_column: ID column name.
        filter_key: API filter key.

    Returns:
        Resolved record source or None.
    """
    resolver = RecordSourceResolver(
        config=config,
        logger=logger,
        extraction_service=extraction_service,
        id_column=id_column,
        filter_key=filter_key,
    )
    return resolver.resolve()


__all__ = [
    "RecordSourceResolver",
    "resolve_record_source",
]
