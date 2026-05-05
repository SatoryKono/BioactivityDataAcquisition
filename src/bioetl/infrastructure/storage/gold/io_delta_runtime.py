"""Prepared payloads and retry helpers for Gold Delta IO mixins."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from types import ModuleType
from typing import TYPE_CHECKING, Protocol, TypeVar, cast

import pyarrow as pa

from bioetl.infrastructure.storage.gold.io_helpers import (
    initialize_scd2_records as _initialize_scd2_records,
)
from bioetl.infrastructure.storage.gold.io_helpers import (
    write_scd2_once as _write_scd2_once,
)

T = TypeVar("T")

if TYPE_CHECKING:
    from datetime import datetime

    from bioetl.domain.types import GoldRecord, ScdConfig
    from bioetl.infrastructure.export.csv_exporter_contract import CsvExporterProtocol


@dataclass(frozen=True, slots=True)
class _SimpleGoldWriteRequest:
    """Normalized request for one simple Gold Delta write."""

    table_path: str
    table_name: str
    records: list[GoldRecord]
    mode: str
    partition_cols: list[str] | None
    primary_keys: list[str] | None = None
    column_order: list[str] | None = None


@dataclass(frozen=True, slots=True)
class _PreparedSimpleGoldWrite:
    """Prepared simple Gold write payload shared across write stages."""

    request: _SimpleGoldWriteRequest
    arrow_data: pa.Table
    schema_mode: str | None


@dataclass(frozen=True, slots=True)
class _PreparedScd2GoldWrite:
    """Prepared SCD2 Gold write carried through retry dispatch."""

    table_path: str
    records: list[GoldRecord]
    business_key: str | list[str]
    scd_config: ScdConfig
    ingestion_ts: datetime
    partition_cols: list[str] | None
    column_order: list[str] | None


class _GoldWriterSimpleDeltaHostProtocol(Protocol):
    """Structural host contract for simple Gold Delta write helpers."""

    csv_exporter: CsvExporterProtocol | None

    async def _run_in_executor(
        self,
        func: Callable[..., object],
        *args: object,
    ) -> object: ...

    def _to_arrow_table(
        self, records: list[GoldRecord], column_order: list[str] | None = None
    ) -> pa.Table: ...


class _GoldWriteAsyncioProtocol(Protocol):
    """Minimal asyncio surface needed by the Gold retry helper."""

    async def sleep(self, delay: float) -> None: ...


class _GoldWriteRetryModuleProtocol(Protocol):
    """Retry-related runtime contract exposed by the canonical gold module."""

    GOLD_WRITE_RETRY_ERRORS: tuple[type[BaseException], ...]
    asyncio: _GoldWriteAsyncioProtocol


class _GoldWriterDeltaModuleProtocol(_GoldWriteRetryModuleProtocol, Protocol):
    """Runtime contract for the simple Delta write path."""

    def write_deltalake(
        self,
        *,
        table_or_uri: str,
        data: pa.RecordBatchReader,
        mode: str,
        partition_by: list[str] | None,
        schema_mode: str | None,
    ) -> None:
        _ = (table_or_uri, data, mode, partition_by, schema_mode)
        raise NotImplementedError


class _GoldWriterScd2HostProtocol(Protocol):
    """Structural host contract for SCD2 Gold Delta write helpers."""

    async def _run_in_executor(
        self,
        func: Callable[..., object],
        *args: object,
    ) -> object: ...

    def _to_arrow_table(
        self, records: list[GoldRecord], column_order: list[str] | None = None
    ) -> pa.Table: ...

    async def _merge_scd2(
        self,
        dt: object,
        records: list[GoldRecord],
        business_key: str | list[str],
        scd_config: ScdConfig,
        ingestion_ts: datetime,
        column_order: list[str] | None = None,
    ) -> None: ...


def _build_simple_gold_write(
    host: _GoldWriterSimpleDeltaHostProtocol,
    request: _SimpleGoldWriteRequest,
) -> _PreparedSimpleGoldWrite:
    """Prepare deterministic Arrow payload and schema mode for simple writes."""
    arrow_data = host._to_arrow_table(
        request.records,
        column_order=request.column_order,
    )
    if request.primary_keys:
        arrow_data = arrow_data.sort_by(
            [(pk, "ascending") for pk in request.primary_keys]
        )
    return _PreparedSimpleGoldWrite(
        request=request,
        arrow_data=arrow_data,
        schema_mode="overwrite" if request.mode == "overwrite" else None,
    )


def _write_prepared_simple_delta(
    module: _GoldWriterDeltaModuleProtocol,
    prepared: _PreparedSimpleGoldWrite,
) -> None:
    """Execute one simple Gold Delta write attempt."""
    module.write_deltalake(
        table_or_uri=prepared.request.table_path,
        data=pa.RecordBatchReader.from_batches(
            prepared.arrow_data.schema, prepared.arrow_data.to_batches()
        ),
        mode=prepared.request.mode,
        partition_by=prepared.request.partition_cols,
        schema_mode=prepared.schema_mode,
    )


async def _execute_prepared_simple_gold_write(
    host: _GoldWriterSimpleDeltaHostProtocol,
    module: _GoldWriterDeltaModuleProtocol,
    prepared: _PreparedSimpleGoldWrite,
) -> None:
    """Run retry-wrapped simple Delta write and optional CSV export."""
    await _run_gold_write_with_retry(
        module,
        lambda: host._run_in_executor(
            _write_prepared_simple_delta,
            module,
            prepared,
        ),
    )
    if host.csv_exporter:
        await host.csv_exporter.export(
            prepared.request.table_name,
            prepared.arrow_data,
            append=prepared.request.mode != "overwrite",
            primary_keys=(
                prepared.request.primary_keys
                if prepared.request.mode != "overwrite"
                else None
            ),
        )


def _prepare_scd2_gold_write(
    *,
    table_path: str,
    records: list[GoldRecord],
    scd_config: ScdConfig,
    partition_cols: list[str] | None,
    ingestion_ts: datetime,
    column_order: list[str] | None,
) -> _PreparedScd2GoldWrite:
    """Normalize and annotate records before SCD2 write retries begin."""
    business_keys = scd_config.business_keys
    records.sort(key=lambda record: tuple(record.get(key) for key in business_keys))
    _initialize_scd2_records(records, scd_config, ingestion_ts)
    return _PreparedScd2GoldWrite(
        table_path=table_path,
        records=records,
        business_key=(
            scd_config.entity_key
            if scd_config.entity_key is not None
            else list(business_keys)
        ),
        scd_config=scd_config,
        ingestion_ts=ingestion_ts,
        partition_cols=partition_cols,
        column_order=column_order,
    )


def _gold_write_retry_delay(attempt: int) -> float:
    """Return deterministic retry delay used by Gold write helpers."""
    return float(0.5 * (2**attempt) + 0.05)


async def _run_gold_write_with_retry(
    module: _GoldWriteRetryModuleProtocol,
    operation: Callable[[], Awaitable[object]],
) -> None:
    """Run one Gold write operation under the canonical retry policy."""
    for attempt in range(3):
        try:
            await operation()
            return
        except module.GOLD_WRITE_RETRY_ERRORS as error:
            if attempt == 2:
                raise error
            await module.asyncio.sleep(_gold_write_retry_delay(attempt))


async def _execute_prepared_scd2_gold_write(
    host: _GoldWriterScd2HostProtocol,
    module: ModuleType,
    prepared: _PreparedScd2GoldWrite,
) -> None:
    """Run retry-wrapped SCD2 Gold write for one prepared request."""
    await _run_gold_write_with_retry(
        cast(_GoldWriteRetryModuleProtocol, module),
        lambda: _write_scd2_once(
            host,
            module=module,
            table_path=prepared.table_path,
            records=prepared.records,
            business_key=prepared.business_key,
            scd_config=prepared.scd_config,
            ingestion_ts=prepared.ingestion_ts,
            partition_cols=prepared.partition_cols,
            column_order=prepared.column_order,
        ),
    )


__all__ = [
    "_PreparedScd2GoldWrite",
    "_PreparedSimpleGoldWrite",
    "_SimpleGoldWriteRequest",
    "_build_simple_gold_write",
    "_execute_prepared_scd2_gold_write",
    "_execute_prepared_simple_gold_write",
    "_gold_write_retry_delay",
    "_prepare_scd2_gold_write",
    "_run_gold_write_with_retry",
]
