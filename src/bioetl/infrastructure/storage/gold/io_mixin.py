"""Write/read and Delta operation helpers for GoldWriter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, cast

import pyarrow as pa

from bioetl.domain.medallion import GoldWriteMode
from bioetl.infrastructure.storage.delta.schema_ops import (
    drop_nondeterministic_persisted_fields,
)
from bioetl.infrastructure.storage.gold.io_delta_mixins import (
    _GoldWriterExecutorArrowMixin,
    _GoldWriterScd2MergeMixin,
    _GoldWriterSimpleDeltaMixin,
)
from bioetl.infrastructure.storage.gold.io_helpers import (
    load_gold_writer_module as _load_gold_writer_module,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    GoldWriteDispatchContext as _GoldWriteDispatchContext,
)
from bioetl.infrastructure.storage.gold.read_cleanup_mixin import (
    GoldWriterReadCleanupMixin,
)

if TYPE_CHECKING:
    from datetime import datetime

    from pandera.polars import DataFrameSchema

    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import GoldRecord, ScdConfig
    from bioetl.infrastructure.export.csv_exporter_contract import CsvExporterPort


class _GoldMergedMetadataWriterProtocol(Protocol):
    """Typed contract for merged-metadata writer implementation."""

    async def _write_gold_merged_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        completed_at: datetime | None = None,
        run_id: str | None = None,
        schema: DataFrameSchema | None = None,
    ) -> None: ...


class _GoldWriteDispatchTargetProtocol(Protocol):
    """Protocol for dispatch targets implemented by concrete write mixins."""

    async def _write_scd2(
        self,
        table_path: str,
        records: list[GoldRecord],
        scd_config: ScdConfig,
        partition_cols: list[str] | None,
        ingestion_ts: datetime,
        column_order: list[str] | None = None,
    ) -> None: ...

    async def _write_simple(
        self,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        mode: str,
        partition_cols: list[str] | None,
        primary_keys: list[str] | None = None,
        _schema: DataFrameSchema | None = None,
        column_order: list[str] | None = None,
    ) -> None: ...


class _GoldMergedWriteHostProtocol(Protocol):
    """Structural host contract for merged Gold write helpers."""

    logger: LoggerPort
    csv_exporter: CsvExporterPort | None
    _resolve_table_path: Callable[[str], str]
    _validate_records_against_schema: Callable[
        [list[GoldRecord], DataFrameSchema], Awaitable[None]
    ]
    _validate_schema_strict: Callable[[DataFrameSchema], None]

    async def _run_in_executor(
        self,
        func: Callable[..., object],
        *args: object,
    ) -> object: ...


@dataclass(frozen=True, slots=True)
class _GoldMergedWriteRequest:
    """Normalized request for one merged Gold write."""

    table_name: str
    records: list[GoldRecord]
    primary_keys: list[str] | None
    schema: DataFrameSchema
    completed_at: datetime | None
    run_id: str | None
    sources_used: list[str] | None
    preserve_column_order: bool = False


@dataclass(frozen=True, slots=True)
class _PreparedGoldMergedWrite:
    """Prepared merged Gold write carried across post-write stages."""

    request: _GoldMergedWriteRequest
    table_path: str
    arrow_table: pa.Table


def _prepare_gold_merged_table(
    *,
    records: list[GoldRecord],
    primary_keys: list[str] | None,
    preserve_column_order: bool,
) -> pa.Table:
    """Build deterministic arrow table for merged Gold output."""
    from bioetl.domain.schemas.column_order import canonical_column_order

    module = _load_gold_writer_module()
    arrow_table = module.coerce_null_types_for_delta(pa.Table.from_pylist(records))
    arrow_table = drop_nondeterministic_persisted_fields(arrow_table)
    if "_ingestion_ts" in arrow_table.column_names:
        persisted_columns = [
            column_name
            for column_name in arrow_table.column_names
            if column_name != "_ingestion_ts"
        ]
        arrow_table = arrow_table.select(persisted_columns)
    if not preserve_column_order:
        ordered_columns = canonical_column_order(list(arrow_table.column_names))
        arrow_table = arrow_table.select(ordered_columns)
    if primary_keys:
        valid_keys = [pk for pk in primary_keys if pk in arrow_table.schema.names]
        if valid_keys:
            arrow_table = arrow_table.sort_by([(pk, "ascending") for pk in valid_keys])
    return arrow_table


async def _prepare_gold_merged_write(
    host: _GoldMergedWriteHostProtocol,
    request: _GoldMergedWriteRequest,
) -> _PreparedGoldMergedWrite:
    """Validate and prepare one merged Gold write request."""
    host._validate_schema_strict(request.schema)
    arrow_table = _prepare_gold_merged_table(
        records=request.records,
        primary_keys=request.primary_keys,
        preserve_column_order=request.preserve_column_order,
    )
    await host._validate_records_against_schema(
        cast("list[GoldRecord]", arrow_table.to_pylist()),
        request.schema,
    )
    return _PreparedGoldMergedWrite(
        request=request,
        table_path=host._resolve_table_path(request.table_name),
        arrow_table=arrow_table,
    )


def _log_prepared_gold_merged_write(
    host: _GoldMergedWriteHostProtocol,
    prepared: _PreparedGoldMergedWrite,
) -> None:
    """Log merged Gold write intent after request preparation."""
    host.logger.info(
        "Writing merged Gold records",
        table_name=prepared.request.table_name,
        path=prepared.table_path,
        records=len(prepared.request.records),
    )


async def _write_gold_merged_delta(
    host: _GoldMergedWriteHostProtocol,
    prepared: _PreparedGoldMergedWrite,
) -> None:
    """Persist merged Gold table to Delta."""
    module = _load_gold_writer_module()
    await host._run_in_executor(
        lambda: module.write_deltalake(
            prepared.table_path,
            prepared.arrow_table,
            mode="overwrite",
            schema_mode="overwrite",
        )
    )


async def _export_gold_merged_csv(
    host: _GoldMergedWriteHostProtocol,
    prepared: _PreparedGoldMergedWrite,
) -> None:
    """Export merged Gold table to CSV when exporter is configured."""
    if host.csv_exporter:
        await host.csv_exporter.export(
            prepared.request.table_name,
            prepared.arrow_table,
            append=False,
        )


async def _write_gold_merged_sidecar(
    host: _GoldMergedWriteHostProtocol,
    prepared: _PreparedGoldMergedWrite,
) -> None:
    """Write merged Gold metadata sidecar after data write completes."""
    metadata_writer = cast(_GoldMergedMetadataWriterProtocol, host)
    await metadata_writer._write_gold_merged_metadata(
        table_path=prepared.table_path,
        table_name=prepared.request.table_name,
        records=prepared.request.records,
        completed_at=prepared.request.completed_at,
        run_id=prepared.request.run_id,
        schema=prepared.request.schema,
    )


async def _complete_gold_merged_write(
    host: _GoldMergedWriteHostProtocol,
    prepared: _PreparedGoldMergedWrite,
) -> None:
    """Run Delta write plus post-write side effects for merged Gold."""
    await _write_gold_merged_delta(host, prepared)
    await _export_gold_merged_csv(host, prepared)
    await _write_gold_merged_sidecar(host, prepared)


async def _execute_gold_merged_write(
    host: _GoldMergedWriteHostProtocol,
    request: _GoldMergedWriteRequest,
) -> None:
    """Prepare, log, and execute one merged Gold write request."""
    prepared = await _prepare_gold_merged_write(host, request)
    _log_prepared_gold_merged_write(host, prepared)
    await _complete_gold_merged_write(host, prepared)


class _GoldWriterMergedDispatchMixin(_GoldWriterExecutorArrowMixin):
    """Merged-write orchestration and mode dispatch."""

    logger: LoggerPort
    csv_exporter: CsvExporterPort | None
    _resolve_table_path: Callable[[str], str]
    _validate_records_against_schema: Callable[
        [list[GoldRecord], DataFrameSchema], Awaitable[None]
    ]
    _validate_schema_strict: Callable[[DataFrameSchema], None]

    async def write_gold_merged(
        self,
        table_name: str,
        records: list[GoldRecord],
        primary_keys: list[str] | None = None,
        *,
        completed_at: datetime | None = None,
        schema: DataFrameSchema | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None:
        """Write merged records to Gold layer with mandatory strict validation."""
        if not records:
            self.logger.warning(
                "No records to write for merged Gold",
                table_name=table_name,
            )
            return
        if schema is None:
            raise ValueError(
                "Merged Gold writes require a registered strict schema: "
                f"table_name={table_name}"
            )

        request = _GoldMergedWriteRequest(
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            schema=schema,
            completed_at=completed_at,
            run_id=run_id,
            sources_used=sources_used,
            preserve_column_order=preserve_column_order,
        )
        await _execute_gold_merged_write(self, request)

    async def _dispatch_write(
        self,
        context: _GoldWriteDispatchContext,
    ) -> None:
        """Dispatch to appropriate write method based on mode."""
        module = _load_gold_writer_module()
        prepared = context.prepared
        request = context.request
        mode = prepared.validated_mode

        if mode == GoldWriteMode.SCD2:
            assert request.ingestion_ts is not None
            assert request.scd_config is not None
            normalized = module._normalize_scd_config(
                request.scd_config,
                request.primary_keys,
            )
            dispatch_target = cast(_GoldWriteDispatchTargetProtocol, self)
            await dispatch_target._write_scd2(
                prepared.table_path,
                request.records,
                normalized,
                request.partition_cols,
                request.ingestion_ts,
                request.column_order,
            )
            return
        dispatch_target = cast(_GoldWriteDispatchTargetProtocol, self)
        await dispatch_target._write_simple(
            prepared.table_path,
            prepared.table_name,
            request.records,
            mode.value,
            request.partition_cols,
            request.primary_keys,
            request.schema,
            request.column_order,
        )


class GoldWriterIOMixin(
    _GoldWriterMergedDispatchMixin,
    _GoldWriterSimpleDeltaMixin,
    _GoldWriterScd2MergeMixin,
    GoldWriterReadCleanupMixin,
):
    """Compose Gold writer IO responsibilities from focused mixins."""


__all__ = ["GoldWriterIOMixin"]
