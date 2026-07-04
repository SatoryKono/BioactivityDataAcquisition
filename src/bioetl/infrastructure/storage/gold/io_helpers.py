"""Helper functions for Gold writer IO and SCD2 flows."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from datetime import datetime

    from bioetl.domain.types import GoldRecord, ScdConfig


def load_gold_writer_module() -> ModuleType:
    """Load canonical `gold_writer` module to preserve monkeypatch points."""
    from importlib import import_module

    return import_module("bioetl.infrastructure.storage.gold_writer")


def initialize_scd2_records(
    records: list[GoldRecord],
    scd_config: ScdConfig,
    ingestion_ts: datetime,
) -> None:
    """Populate SCD2 metadata fields before writing."""
    version_col = scd_config.version_col
    valid_from_col = scd_config.valid_from_col
    valid_to_col = scd_config.valid_to_col
    current_flag_col = scd_config.current_flag_col
    ts_iso = ingestion_ts.isoformat()
    for record in records:
        record[valid_from_col] = ts_iso
        record[valid_to_col] = None
        record[current_flag_col] = True
        record[version_col] = record.get(version_col, 1)


class _GoldWriterSCDHostProtocol(Protocol):
    """Typed host contract used by SCD2 helper functions."""

    async def _run_in_executor(
        self, func: Callable[..., object], *args: object
    ) -> object: ...

    async def _merge_scd2(
        self,
        dt: Any,  # Any: deltalake DeltaTable untyped
        records: list[GoldRecord],
        business_key: str | list[str],
        scd_config: ScdConfig,
        ingestion_ts: datetime,
        column_order: list[str] | None = None,
    ) -> None: ...

    def _to_arrow_table(
        self, records: list[GoldRecord], column_order: list[str] | None = None
    ) -> object: ...


async def write_scd2_once(
    writer: _GoldWriterSCDHostProtocol,
    *,
    module: ModuleType,
    table_path: str,
    records: list[GoldRecord],
    business_key: str | list[str],
    scd_config: ScdConfig,
    ingestion_ts: datetime,
    partition_cols: list[str] | None,
    column_order: list[str] | None,
) -> None:
    """Execute one SCD2 write attempt with merge-or-create flow."""
    try:
        dt = await writer._run_in_executor(lambda: module.DeltaTable(table_path))
        await writer._merge_scd2(
            dt,
            records,
            business_key,
            scd_config,
            ingestion_ts,
            column_order,
        )
    except module.TableNotFoundError:
        arrow_data = writer._to_arrow_table(records, column_order=column_order)
        await writer._run_in_executor(
            lambda: module.write_deltalake(
                table_or_uri=table_path,
                data=arrow_data,
                mode="append",
                partition_by=partition_cols,
            )
        )


__all__ = [
    "initialize_scd2_records",
    "load_gold_writer_module",
    "write_scd2_once",
]
