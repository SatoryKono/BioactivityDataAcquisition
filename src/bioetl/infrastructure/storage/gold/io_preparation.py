"""Dataclasses and preparation helpers for Gold merged writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import cast

import pyarrow as pa
from pandera.polars import DataFrameSchema

from bioetl.domain.types import GoldRecord
from bioetl.infrastructure.storage.delta.schema_ops import (
    drop_nondeterministic_persisted_fields,
)
from bioetl.infrastructure.storage.gold.io_helpers import (
    load_gold_writer_module as _load_gold_writer_module,
)
from bioetl.infrastructure.storage.gold.io_protocols import _GoldMergedWriteHostProtocol

__all__ = [
    "_GoldMergedWriteRequest",
    "_PreparedGoldMergedWrite",
    "_log_prepared_gold_merged_write",
    "_prepare_gold_merged_table",
    "_prepare_gold_merged_write",
]


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
