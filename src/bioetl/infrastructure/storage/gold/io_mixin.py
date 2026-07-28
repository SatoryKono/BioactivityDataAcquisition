# pyright: reportUninitializedInstanceVariable=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
# pyright: reportArgumentType=false
# pyright: reportInvalidCast=false
# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Write/read and Delta operation helpers for GoldWriter.

This module re-exports from split modules for backward compatibility.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast

from bioetl.domain.medallion import GoldWriteMode

if TYPE_CHECKING:
    from datetime import datetime

    from pandera.polars import DataFrameSchema

    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import GoldRecord
    from bioetl.infrastructure.export.csv_exporter_contract import CsvExporterProtocol

# Re-export from split modules
from bioetl.infrastructure.storage.gold.io_delta_mixins import (
    _GoldWriterExecutorArrowMixin,
    _GoldWriterScd2MergeMixin,
    _GoldWriterSimpleDeltaMixin,
)
from bioetl.infrastructure.storage.gold.io_helpers import (
    load_gold_writer_module as _load_gold_writer_module,
)
from bioetl.infrastructure.storage.gold.io_protocols import (
    _GoldWriteDispatchTargetProtocol,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    GoldWriteDispatchContext as _GoldWriteDispatchContext,
)
from bioetl.infrastructure.storage.gold.read_cleanup_mixin import (
    GoldWriterReadCleanupMixin,
)

__all__ = ["GoldWriterIOMixin"]


class _GoldWriterMergedDispatchMixin(_GoldWriterExecutorArrowMixin):
    """Merged-write orchestration and mode dispatch."""

    logger: LoggerPort
    csv_exporter: CsvExporterProtocol | None
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

        from bioetl.infrastructure.storage.gold.io_execution import (
            _execute_gold_merged_write,
        )
        from bioetl.infrastructure.storage.gold.io_preparation import (
            _GoldMergedWriteRequest,
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
