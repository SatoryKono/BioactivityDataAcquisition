"""Gold layer writer — RULES.md §2.1.1, REQ-DATA-009/010, REQ-CONTRACT-001."""

from __future__ import annotations

import asyncio  # noqa: F401 - compatibility monkeypatch target in tests
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake  # noqa: F401
from deltalake.exceptions import TableNotFoundError  # noqa: F401

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.types import GoldRecord, RunID, ScdConfig
from bioetl.infrastructure.storage.base_delta_writer import (
    BaseDeltaWriter,
    coerce_null_types_for_delta,  # noqa: F401
)
from bioetl.infrastructure.storage.gold_writer_io_mixin import GoldWriterIOMixin
from bioetl.infrastructure.storage.gold_writer_metadata_mixin import (
    GoldWriterMetadataMixin,
)
from bioetl.infrastructure.storage.gold_writer_validation_mixin import (
    GoldWriterValidationMixin,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pandera.polars import DataFrameSchema

    from bioetl.domain.ports import (
        AuditPort,
        LoggerPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
        TracingPort,
    )
    from bioetl.infrastructure.export.csv_exporter import CsvExporter

__all__ = ["GoldWriteMode", "GoldWriter"]

_SCD_KEY_MAP = {
    "valid_from": "valid_from_col",
    "valid_to": "valid_to_col",
    "is_current": "current_flag_col",
    "version": "version_col",
}

GOLD_WRITE_RETRY_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    KeyError,
    pa.ArrowException,
)


def _normalize_scd_config(
    scd_config: ScdConfig,
    primary_keys: list[str] | None,
) -> ScdConfig:
    """Normalize YAML scd_config keys to gold_writer expected format."""
    out: dict[str, Any] = dict(scd_config)  # Any: ScdConfig is heterogeneous
    if "business_key" not in out and primary_keys:
        out["business_key"] = (
            primary_keys[0] if len(primary_keys) == 1 else primary_keys
        )
    for src, dst in _SCD_KEY_MAP.items():
        if src in out and dst not in out:
            out[dst] = out[src]
    return cast(ScdConfig, out)


class GoldWriter(
    GoldWriterValidationMixin,
    GoldWriterIOMixin,
    GoldWriterMetadataMixin,
    BaseDeltaWriter,
):
    """Gold layer writer: strict Pandera validation, Delta Lake, and SCD2."""

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        tracing: TracingPort | None = None,
        csv_exporter: CsvExporter | None = None,
        audit: AuditPort | None = None,
        metadata_writer: MetadataWriterPort | None = None,
        metadata_coordinator: MetadataCoordinatorPort | None = None,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
        flat_structure: bool = False,
    ) -> None:
        """Initialize Gold writer and optional observability/metadata ports."""
        super().__init__(base_path, logger, flat_structure=flat_structure)

        if tracing is None:
            from bioetl.domain.ports import NoOpTracing

            tracing = NoOpTracing()

        self.csv_exporter = csv_exporter
        self._audit = audit
        self._tracing: TracingPort = tracing

        if metadata_writer is None:
            from bioetl.domain.ports import NoOpMetadataWriter

            metadata_writer = NoOpMetadataWriter()
        self._metadata_writer: MetadataWriterPort = metadata_writer
        self._metadata_coordinator: MetadataCoordinatorPort | None = (
            metadata_coordinator
        )

        self._transform_version = transform_version
        self._transform_steps = transform_steps or ()

    async def write_gold(
        self,
        table_name: str,
        records: list[GoldRecord],
        schema: DataFrameSchema,
        primary_keys: list[str] | None = None,
        mode: str = "overwrite",
        partition_cols: list[str] | None = None,
        scd_config: ScdConfig | None = None,
        *,
        column_order: list[str] | None = None,
        ingestion_ts: datetime | None = None,
        run_id: RunID | None = None,
        silver_refs: list[Any] | None = None,  # Any: SilverRef heterogeneous
    ) -> None:
        """Write validated records to Gold layer."""
        tracer = self._tracing.get_tracer(__name__)
        with tracer.start_as_current_span("write_gold") as span:
            span.set_attribute("table_name", table_name)
            span.set_attribute("mode", mode)
            span.set_attribute("record_count", len(records))

            validated_mode = self._validate_write_mode(mode)
            self._validate_records(records)
            self._validate_scd2_requirements(validated_mode, scd_config, ingestion_ts)
            self._validate_schema_strict(schema)
            await self._validate_records_against_schema(records, schema)

            table_path = self._resolve_table_path(table_name)

            await self._dispatch_write(
                validated_mode,
                table_path,
                table_name,
                records,
                partition_cols,
                primary_keys,
                schema,
                scd_config,
                ingestion_ts,
                column_order,
            )

            if self._audit:
                await self._log_gold_audit(
                    table_name=table_name,
                    records=records,
                    mode=validated_mode,
                    ingestion_ts=ingestion_ts,
                    run_id=run_id,
                )

            await self._write_gold_metadata(
                table_path=table_path,
                table_name=table_name,
                records=records,
                mode=validated_mode,
                scd_config=scd_config,
                ingestion_ts=ingestion_ts,
                run_id=run_id,
                silver_refs=silver_refs,
                gold_schema=schema,
            )
