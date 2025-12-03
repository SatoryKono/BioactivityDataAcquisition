"""Default factories for record sources and normalization services."""
from __future__ import annotations

from typing import Any

from bioetl.clients.records.contracts import (
    RecordNormalizationServiceABC,
    RecordSourceABC,
)
from bioetl.clients.records.impl.api_record_source import ChemblApiRecordSourceImpl
from bioetl.clients.records.impl.csv_record_source import CsvRecordSourceImpl
from bioetl.clients.records.impl.id_only_record_source import IdOnlyRecordSourceImpl
from bioetl.clients.chembl.impl.chembl_normalization_service import (
    ChemblNormalizationServiceImpl,
)
from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.records import NormalizedRecord
from bioetl.infrastructure.config.models import ChemblSourceConfig, PipelineConfig


def _resolve_id_column(config: PipelineConfig) -> str:
    explicit = config.primary_key
    if not explicit and config.pipeline and "primary_key" in config.pipeline:
        explicit = config.pipeline["primary_key"]
    return explicit or f"{config.entity_name}_id"


def default_record_source(
    config: PipelineConfig,
    extraction_service: ExtractionServiceABC,
    *,
    limit: int | None = None,
) -> RecordSourceABC:
    """Return the appropriate record source based on CLI configuration."""

    input_path = config.cli.get("input_file")
    id_column = _resolve_id_column(config)

    if input_path:
        header = CsvRecordSourceImpl.peek_columns(input_path)
        is_full_dataset = config.cli.get("input_full_dataset")

        if is_full_dataset is None:
            is_full_dataset = len(header) > 2

        if is_full_dataset:
            return CsvRecordSourceImpl(path=input_path, limit=limit)

        filter_key = f"{id_column}__in"
        source_cfg = config.get_source_config("chembl")
        if not isinstance(source_cfg, ChemblSourceConfig):
            raise TypeError("Expected ChemblSourceConfig")

        batch_size = source_cfg.resolve_effective_batch_size(
            limit=limit, hard_cap=25
        )

        return IdOnlyRecordSourceImpl(
            path=input_path,
            id_column=id_column,
            extraction_service=extraction_service,
            entity=config.entity_name,
            filter_key=filter_key,
            batch_size=batch_size,
        )

    filters: dict[str, Any] = {}
    if config.pipeline:
        filters.update(config.pipeline)
    return ChemblApiRecordSourceImpl(
        extraction_service=extraction_service,
        entity=config.entity_name,
        filters=filters,
        limit=limit,
    )


def default_normalization_service(
    config: PipelineConfig,
) -> RecordNormalizationServiceABC:
    """Create default normalization service for record-level processing."""

    fields = config.fields or []
    normalization_cfg = config.normalization
    return ChemblNormalizationServiceImpl(
        fields=fields,
        case_sensitive_fields=normalization_cfg.case_sensitive_fields,
        id_fields=normalization_cfg.id_fields,
    )


__all__ = [
    "default_record_source",
    "default_normalization_service",
    "NormalizedRecord",
]
