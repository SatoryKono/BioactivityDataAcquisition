"""Post-write helpers for SilverWriter."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.storage.silver.operations.postwrite_operations import (
    _complete_silver_write_pipeline_impl,
    _finalize_silver_postwrite_result,
)
from bioetl.infrastructure.storage.silver.validation_operations import (
    _PreparedSilverWritePayload,
)

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.domain.types import BatchID, RunID, RunType
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
    def run_id(self) -> RunID | None: ...

    @property
    def run_type(self) -> RunType | None: ...

    @property
    def source_batch_id(self) -> BatchID | None: ...

    @property
    def ingestion_ts(self) -> datetime | None: ...

    @property
    def quarantined_count(self) -> int | None: ...

    @property
    def validation_errors(self) -> Sequence[str] | None: ...

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
        run_id: RunID | None,
        run_type: RunType | None,
        source_batch_id: BatchID | None,
        ingestion_ts: datetime | None,
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
        source_batch_id: BatchID | None,
        quarantined_count: int | None = None,
        validation_errors: Sequence[str] | None = None,
        started_at: datetime,
        start_perf: float,
    ) -> SilverWriteResult | None: ...

    async def _run_postwrite_export(
        self,
        *,
        ctx: _SilverWritePostwriteContext,
        payload: _PreparedSilverWritePayload,
    ) -> None: ...

    async def _run_postwrite_audit(
        self,
        *,
        ctx: _SilverWritePostwriteContext,
        payload: _PreparedSilverWritePayload,
    ) -> None: ...

    async def _finalize_postwrite_result(
        self,
        *,
        ctx: _SilverWritePostwriteContext,
        payload: _PreparedSilverWritePayload,
    ) -> SilverWriteResult | None: ...


class SilverWriterPostwriteMixin:
    """Post-write orchestration extracted from ``SilverWriter``."""

    async def _run_postwrite_export(
        self: _SilverWriterPostwriteSelf,
        *,
        ctx: _SilverWritePostwriteContext,
        payload: _PreparedSilverWritePayload,
    ) -> None:
        """Run the legacy mixin export branch via the compatibility hook."""
        await self._maybe_export_csv(
            table_name=ctx.table_name,
            arrow_data=payload.arrow_data,
            mode=ctx.mode,
            validated_mode=payload.validated_mode,
            primary_keys=ctx.primary_keys,
        )

    async def _run_postwrite_audit(
        self: _SilverWriterPostwriteSelf,
        *,
        ctx: _SilverWritePostwriteContext,
        payload: _PreparedSilverWritePayload,
    ) -> None:
        """Run the legacy mixin audit branch via the compatibility hook."""
        await self._maybe_log_silver_audit(
            table_name=ctx.table_name,
            records=payload.records,
            mode=payload.validated_mode,
            run_id=ctx.run_id,
            run_type=ctx.run_type,
            source_batch_id=ctx.source_batch_id,
            ingestion_ts=ctx.ingestion_ts,
        )

    async def _finalize_postwrite_result(
        self: _SilverWriterPostwriteSelf,
        *,
        ctx: _SilverWritePostwriteContext,
        payload: _PreparedSilverWritePayload,
    ) -> SilverWriteResult | None:
        """Finalize the legacy mixin postwrite flow."""
        return await _finalize_silver_postwrite_result(
            self._finalize_silver_write_result,
            ctx=ctx,
            payload=payload,
        )

    async def _complete_silver_write_pipeline(
        self: _SilverWriterPostwriteSelf,
        *,
        ctx: _SilverWritePostwriteContext,
        payload: _PreparedSilverWritePayload,
    ) -> SilverWriteResult | None:
        """Run post-write stages: CSV export, audit, and result finalization."""
        return await _complete_silver_write_pipeline_impl(
            self,
            ctx=ctx,
            payload=payload,
        )
