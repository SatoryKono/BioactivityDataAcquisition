"""Protocol contracts for Gold Delta IO runtime helpers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from bioetl.domain.types import GoldRecord, ScdConfig
from bioetl.infrastructure.export.csv_exporter_contract import CsvExporterProtocol


class GoldWriterSimpleDeltaHostProtocol(Protocol):
    """Structural host contract for simple Gold Delta write helpers."""

    csv_exporter: CsvExporterProtocol | None

    async def _run_in_executor[ResultT](
        self,
        func: Callable[..., ResultT],
        *args: object,
    ) -> ResultT: ...

    def _to_arrow_table(
        self, records: list[GoldRecord], column_order: list[str] | None = None
    ) -> object: ...


class GoldWriteAsyncioProtocol(Protocol):
    """Minimal asyncio surface needed by the Gold retry helper."""

    async def sleep(self, delay: float) -> None: ...


class GoldWriteRetryModuleProtocol(Protocol):
    """Retry-related runtime contract exposed by the canonical gold module."""

    GOLD_WRITE_RETRY_ERRORS: tuple[type[BaseException], ...]
    asyncio: GoldWriteAsyncioProtocol


class GoldWriterDeltaModuleProtocol(GoldWriteRetryModuleProtocol, Protocol):
    """Runtime contract for the simple Delta write path."""

    def write_deltalake(
        self,
        *,
        table_or_uri: str,
        data: object,
        mode: str,
        partition_by: list[str] | None,
        schema_mode: str | None,
    ) -> None:
        _ = (table_or_uri, data, mode, partition_by, schema_mode)
        raise NotImplementedError


class GoldWriterScd2HostProtocol(Protocol):
    """Structural host contract for SCD2 Gold Delta write helpers."""

    async def _run_in_executor[ResultT](
        self,
        func: Callable[..., ResultT],
        *args: object,
    ) -> ResultT: ...

    def _to_arrow_table(
        self, records: list[GoldRecord], column_order: list[str] | None = None
    ) -> object: ...

    async def _merge_scd2(
        self,
        dt: Any,  # Any: deltalake DeltaTable has no complete type stubs
        records: list[GoldRecord],
        business_key: str | list[str],
        scd_config: ScdConfig,
        ingestion_ts: datetime,
        column_order: list[str] | None = None,
    ) -> None: ...


__all__ = [
    "GoldWriteRetryModuleProtocol",
    "GoldWriterDeltaModuleProtocol",
    "GoldWriterScd2HostProtocol",
    "GoldWriterSimpleDeltaHostProtocol",
]
