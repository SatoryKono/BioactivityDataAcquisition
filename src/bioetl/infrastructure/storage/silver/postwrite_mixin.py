"""Post-write helpers for SilverWriter."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from bioetl.infrastructure.storage.silver.validation_operations import (
    _PreparedSilverWritePayload,
)

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.domain.medallion import SilverWriteMode
    from bioetl.domain.types import BronzeRecord
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult


class _SilverWritePostwriteContext(Protocol):
    """Structural type for the write execution context used after Delta write."""

    @property
    def table_name(self) -> str: ...

    @property
    def mode(self) -> str: ...

    @property
    def primary_keys(self) -> list[str]: ...

    @property
    def bronze_refs(self) -> list[BronzeWriteResult] | None: ...

    @property
    def partition_cols(self) -> list[str] | None: ...

    @property
    def started_at(self) -> datetime: ...

    @property
    def start_perf(self) -> float: ...


class _SilverWriterPostwriteSelf(Protocol):
    """Structural type for mixin self dependencies."""

    async def _maybe_export_csv(
        self,
        *,
        table_name: str,
        arrow_data: pa.Table,
        mode: str,
        validated_mode: SilverWriteMode,
        primary_keys: list[str],
    ) -> None: ...

    async def _maybe_log_silver_audit(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        mode: SilverWriteMode,
    ) -> None: ...

    async def _finalize_silver_write_result(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        table_path: str,
        primary_keys: list[str],
        validated_mode: SilverWriteMode,
        bronze_refs: list[BronzeWriteResult] | None,
        partition_cols: list[str] | None,
        started_at: datetime,
        start_perf: float,
    ) -> SilverWriteResult | None: ...


class SilverWriterPostwriteMixin:
    """Post-write orchestration extracted from ``SilverWriter``."""

    async def _complete_silver_write_pipeline(
        self: _SilverWriterPostwriteSelf,
        *,
        ctx: _SilverWritePostwriteContext,
        payload: _PreparedSilverWritePayload,
    ) -> SilverWriteResult | None:
        """Run post-write stages: CSV export, audit, and result finalization."""
        await self._maybe_export_csv(
            table_name=ctx.table_name,
            arrow_data=payload.arrow_data,
            mode=ctx.mode,
            validated_mode=payload.validated_mode,
            primary_keys=ctx.primary_keys,
        )
        await self._maybe_log_silver_audit(
            table_name=ctx.table_name,
            records=payload.records,
            mode=payload.validated_mode,
        )
        return await self._finalize_silver_write_result(
            table_name=ctx.table_name,
            records=payload.records,
            table_path=payload.table_path,
            primary_keys=ctx.primary_keys,
            validated_mode=payload.validated_mode,
            bronze_refs=ctx.bronze_refs,
            partition_cols=ctx.partition_cols,
            started_at=ctx.started_at,
            start_perf=ctx.start_perf,
        )
