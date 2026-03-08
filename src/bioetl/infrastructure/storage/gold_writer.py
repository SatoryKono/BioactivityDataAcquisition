"""Gold layer writer — RULES.md §2.1.1, REQ-DATA-009/010, REQ-CONTRACT-001."""

from __future__ import annotations

import asyncio  # noqa: F401 - compatibility monkeypatch target in tests
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake  # noqa: F401
from deltalake.exceptions import TableNotFoundError  # noqa: F401

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.types import GoldRecord, JsonDict, RunID, ScdConfig
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
    from bioetl.domain.value_objects.silver_result import SilverWriteResult
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
    """Normalize YAML scd_config keys to gold_writer expected format.

    Args:
        scd_config: Raw SCD configuration from pipeline YAML.
        primary_keys: Optional primary key list used to fill in missing business_key.

    Returns:
        Normalized ScdConfig with gold_writer-compatible key names.
    """
    out: JsonDict = dict(scd_config)  # Any: ScdConfig is heterogeneous
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
        """Initialize Gold writer and optional observability/metadata ports.

        Args:
            base_path: Root directory for Gold layer Delta Lake tables.
            logger: Structured logger for write events and errors.
            tracing: Optional tracing port for span propagation; defaults to NoOpTracing.
            csv_exporter: Optional CSV exporter for post-write snapshots; disabled when None.
            audit: Optional audit port for Gold lineage logging; disabled when None.
            metadata_writer: Optional sidecar metadata writer; defaults to NoOpMetadataWriter.
            metadata_coordinator: Optional coordinator for metadata orchestration; disabled when None.
            transform_version: Optional version string embedded in Gold metadata.
            transform_steps: Optional tuple of transform step names for lineage.
            flat_structure: When True, omit the table-based subdirectory hierarchy.
        """
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
        silver_refs: list[SilverWriteResult] | None = None,
    ) -> None:
        """Write validated records to Gold layer.

        Args:
            table_name: Logical Delta table name (e.g., ``"chembl_activity"``).
            records: Fully transformed and validated Gold records to write.
            schema: Pandera DataFrameSchema for strict validation before write.
            primary_keys: Optional business key fields used for SCD2 merge;
                unused for overwrite mode.
            mode: Write mode string (``"overwrite"`` or ``"scd2"``).
            partition_cols: Optional column names for Delta table partitioning;
                disables partitioning when None.
            scd_config: Optional SCD type-2 configuration including column
                mappings and business key definitions; required for ``"scd2"`` mode.
            column_order: Optional explicit column ordering applied before writing;
                uses schema order when None.
            ingestion_ts: Optional UTC timestamp embedded in Gold metadata;
                uses current time when None.
            run_id: Optional pipeline run ID for lineage; excluded from metadata
                when None.
            silver_refs: Optional Silver write results included as lineage
                references in Gold metadata.
        """
        tracer = self._tracing.get_tracer(__name__)
        with tracer.start_as_current_span("write_gold") as span:
            self._set_write_span_attributes(span, table_name, mode, len(records))
            validated_mode, table_path = await self._prepare_write_gold(
                table_name=table_name,
                records=records,
                mode=mode,
                schema=schema,
                scd_config=scd_config,
                ingestion_ts=ingestion_ts,
            )
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
            await self._post_write_gold(
                table_path=table_path,
                table_name=table_name,
                records=records,
                validated_mode=validated_mode,
                ingestion_ts=ingestion_ts,
                run_id=run_id,
                scd_config=scd_config,
                silver_refs=silver_refs,
                schema=schema,
            )

    async def _prepare_write_gold(
        self,
        *,
        table_name: str,
        records: list[GoldRecord],
        mode: str,
        schema: DataFrameSchema,
        scd_config: ScdConfig | None,
        ingestion_ts: datetime | None,
    ) -> tuple[GoldWriteMode, str]:
        """Run validation steps and resolve target path.

        Args:
            table_name: Logical Delta table name for path resolution.
            records: Gold records to validate before writing.
            mode: Write mode string passed through for validation.
            schema: Pandera schema used for strict record validation.
            scd_config: Optional SCD2 config; required for ``"scd2"`` mode.
            ingestion_ts: Optional UTC timestamp required for SCD2 writes.

        Returns:
            Tuple of (validated GoldWriteMode enum, resolved filesystem path string).
        """
        validated_mode = self._validate_write_mode(mode)
        self._validate_records(records)
        self._validate_scd2_requirements(validated_mode, scd_config, ingestion_ts)
        self._validate_schema_strict(schema)
        await self._validate_records_against_schema(records, schema)
        return validated_mode, self._resolve_table_path(table_name)

    async def _post_write_gold(
        self,
        *,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        validated_mode: GoldWriteMode,
        ingestion_ts: datetime | None,
        run_id: RunID | None,
        scd_config: ScdConfig | None,
        silver_refs: list[SilverWriteResult] | None,
        schema: DataFrameSchema,
    ) -> None:
        """Emit audit and metadata after successful Gold write.

        Args:
            table_path: Resolved filesystem path of the Gold Delta table.
            table_name: Logical Delta table name for audit and metadata.
            records: Gold records that were written; used for count reporting.
            validated_mode: Resolved write mode enum from the preparation step.
            ingestion_ts: UTC ingestion timestamp embedded in metadata; None
                skips timestamp in audit output.
            run_id: Pipeline run ID for lineage; None excludes it from audit.
            scd_config: SCD2 configuration passed to metadata writers.
            silver_refs: Silver write results for lineage metadata.
            schema: Pandera schema passed to Gold metadata writers.
        """
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

    @staticmethod
    def _set_write_span_attributes(
        span: Any,  # Any: tracing SDK span protocol is runtime-provided
        table_name: str,
        mode: str,
        record_count: int,
    ) -> None:
        """Set standard tracing attributes for write_gold span.

        Args:
            span: Active OpenTelemetry span to annotate.
            table_name: Logical Delta table name set as span attribute.
            mode: Write mode string set as span attribute.
            record_count: Number of records being written set as span attribute.
        """
        span.set_attribute("table_name", table_name)
        span.set_attribute("mode", mode)
        span.set_attribute("record_count", record_count)
