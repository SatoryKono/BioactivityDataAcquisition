"""Gold layer writer — RULES.md §2.1.1, REQ-DATA-009/010, REQ-CONTRACT-001."""

from __future__ import annotations

import asyncio  # noqa: F401 - compatibility monkeypatch target in tests
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake  # noqa: F401
from deltalake.exceptions import TableNotFoundError  # noqa: F401

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.ports import (
    AuditPort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    TracingPort,
)
from bioetl.domain.types import GoldRecord, RunID, ScdConfig
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.base_delta_writer import (
    BaseDeltaWriter,
    coerce_null_types_for_delta,  # noqa: F401
)
from bioetl.infrastructure.storage.gold_writer_io_mixin import GoldWriterIOMixin
from bioetl.infrastructure.storage.gold_writer_metadata_mixin import (
    GoldWriterMetadataMixin,
)
from bioetl.infrastructure.storage.gold_writer_pipeline_helpers import (
    GoldWriteDispatchContext as _GoldWriteDispatchContext,
)
from bioetl.infrastructure.storage.gold_writer_pipeline_helpers import (
    GoldWritePostwriteContext as _GoldWritePostwriteContext,
)
from bioetl.infrastructure.storage.gold_writer_pipeline_helpers import (
    GoldWriteRequest as _GoldWriteRequest,
)
from bioetl.infrastructure.storage.gold_writer_pipeline_helpers import (
    PreparedGoldWriteContext as _PreparedGoldWriteContext,
)
from bioetl.infrastructure.storage.gold_writer_pipeline_helpers import (
    post_write_gold as _post_write_gold_impl,
)
from bioetl.infrastructure.storage.gold_writer_pipeline_helpers import (
    prepare_gold_write as _prepare_write_gold_impl,
)
from bioetl.infrastructure.storage.gold_writer_pipeline_helpers import (
    set_gold_write_span_attributes as _set_write_span_attributes_impl,
)
from bioetl.infrastructure.storage.gold_writer_runtime_helpers import (
    GoldWriterRuntimeServices,
    build_gold_writer_runtime_services,
)
from bioetl.infrastructure.storage.gold_writer_validation_mixin import (
    GoldWriterValidationMixin,
)

if TYPE_CHECKING:
    from pandera.polars import DataFrameSchema

    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.value_objects.silver_result import SilverWriteResult

__all__ = ["GoldWriteMode", "GoldWriter"]

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
    """Compatibility wrapper preserving canonical monkeypatch/import path."""
    from bioetl.infrastructure.storage.gold_writer_pipeline_helpers import (
        normalize_scd_config,
    )

    return normalize_scd_config(scd_config, primary_keys)


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
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
        runtime_services: GoldWriterRuntimeServices | None = None,
        flat_structure: bool = False,
        **legacy_kwargs: object,
    ) -> None:
        """Initialize Gold writer and optional observability/metadata ports.

        Args:
            base_path: Root directory for Gold layer Delta Lake tables.
            logger: Structured logger for write events and errors.
            transform_version: Optional version string embedded in Gold metadata.
            transform_steps: Optional tuple of transform step names for lineage.
            runtime_services: Optional grouped runtime collaborators for tracing,
                metadata, audit, and optional CSV export.
            flat_structure: When True, omit the table-based subdirectory hierarchy.
        """
        csv_exporter = cast(
            "CsvExporter | None", legacy_kwargs.pop("csv_exporter", None)
        )
        tracing = cast("TracingPort | None", legacy_kwargs.pop("tracing", None))
        audit = cast("AuditPort | None", legacy_kwargs.pop("audit", None))
        metadata_writer = cast(
            "MetadataWriterPort | None",
            legacy_kwargs.pop("metadata_writer", None),
        )
        metadata_coordinator = cast(
            "MetadataCoordinatorPort | None",
            legacy_kwargs.pop("metadata_coordinator", None),
        )
        if legacy_kwargs:
            unexpected = ", ".join(sorted(legacy_kwargs))
            raise TypeError(f"Unexpected GoldWriter options: {unexpected}")

        super().__init__(base_path, logger, flat_structure=flat_structure)
        services = runtime_services or build_gold_writer_runtime_services(
            csv_exporter=csv_exporter,
            tracing=tracing,
            audit=audit,
            metadata_writer=metadata_writer,
            metadata_coordinator=metadata_coordinator,
        )
        self.csv_exporter = services.csv_exporter
        self._audit = services.audit
        self._tracing = services.tracing
        self._metadata_writer = services.metadata_writer
        self._metadata_coordinator = services.metadata_coordinator
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
            normalized_scd_config = (
                ScdConfig.from_mapping(scd_config, primary_keys=primary_keys)
                if isinstance(scd_config, Mapping)
                else scd_config
            )
            request = _GoldWriteRequest(
                table_name=table_name,
                records=records,
                schema=schema,
                primary_keys=primary_keys,
                mode=mode,
                partition_cols=partition_cols,
                scd_config=normalized_scd_config,
                column_order=column_order,
                ingestion_ts=ingestion_ts,
                run_id=run_id,
                silver_refs=silver_refs,
            )
            self._set_write_span_attributes(
                span,
                request.table_name,
                request.mode,
                len(request.records),
            )
            prepared = await self._prepare_write_gold(
                table_name=request.table_name,
                records=request.records,
                mode=request.mode,
                schema=request.schema,
                scd_config=request.scd_config,
                ingestion_ts=request.ingestion_ts,
            )
            await self._dispatch_write(
                _GoldWriteDispatchContext(
                    prepared=prepared,
                    request=request,
                )
            )
            await self._post_write_gold(
                _GoldWritePostwriteContext(
                    prepared=prepared,
                    records=request.records,
                    ingestion_ts=request.ingestion_ts,
                    run_id=request.run_id,
                    scd_config=request.scd_config,
                    silver_refs=request.silver_refs,
                    schema=request.schema,
                )
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
    ) -> _PreparedGoldWriteContext:
        """Run validation steps and resolve target path.

        Args:
            table_name: Logical Delta table name for path resolution.
            records: Gold records to validate before writing.
            mode: Write mode string passed through for validation.
            schema: Pandera schema used for strict record validation.
            scd_config: Optional SCD2 config; required for ``"scd2"`` mode.
            ingestion_ts: Optional UTC timestamp required for SCD2 writes.

        Returns:
            Prepared write context with validated mode and resolved target path.
        """
        return await _prepare_write_gold_impl(
            self,
            table_name=table_name,
            records=records,
            mode=mode,
            schema=schema,
            scd_config=scd_config,
            ingestion_ts=ingestion_ts,
        )

    async def _post_write_gold(
        self,
        context: _GoldWritePostwriteContext,
    ) -> None:
        """Emit audit and metadata after successful Gold write.

        Args:
            context: Named post-write context containing prepared path/mode,
                records, lineage inputs, and schema for metadata emission.
        """
        await _post_write_gold_impl(self, context)

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
        _set_write_span_attributes_impl(span, table_name, mode, record_count)
