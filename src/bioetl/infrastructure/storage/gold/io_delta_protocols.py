"""Protocol contracts for Gold Delta IO runtime helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol


class GoldWriterSimpleDeltaHostProtocol(Protocol):
    """Structural host contract for simple Gold Delta write helpers."""

    csv_exporter: object | None

    async def _run_in_executor(
        self,
        func: Callable[..., object],
        *args: object,
    ) -> object: ...

    def _to_arrow_table(
        self, records: list[dict[str, object]], column_order: list[str] | None = None
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

    async def _run_in_executor(
        self,
        func: Callable[..., object],
        *args: object,
    ) -> object: ...

    def _to_arrow_table(
        self, records: list[dict[str, object]], column_order: list[str] | None = None
    ) -> object: ...

    async def _merge_scd2(
        self,
        dt: object,
        records: list[dict[str, object]],
        business_key: str | list[str],
        scd_config: object,
        ingestion_ts: object,
        column_order: list[str] | None = None,
    ) -> None: ...


__all__ = [
    "GoldWriteRetryModuleProtocol",
    "GoldWriterDeltaModuleProtocol",
    "GoldWriterScd2HostProtocol",
    "GoldWriterSimpleDeltaHostProtocol",
]
