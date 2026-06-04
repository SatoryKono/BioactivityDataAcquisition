"""Postwrite runtime contracts for Silver writer services."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Protocol

import pyarrow as pa

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.validation_operations import (
    _PreparedSilverWritePayload,
)

__all__ = [
    "_SilverMaintenancePostwriteOps",
    "_SilverMetadataPostwriteOps",
    "_SilverPostwriteExecutorProtocol",
    "_SilverPostwriteFinalizerProtocol",
    "_SilverPostwriteHostProtocol",
    "_SilverWritePostwriteContext",
]


class _SilverMaintenancePostwriteOps(Protocol):
    async def maybe_export_csv(
        self,
        *,
        table_name: str,
        arrow_data: pa.Table,
        export_path: str,
        primary_keys: list[str],
        audit_timestamp: datetime | None = None,
    ) -> None: ...


class _SilverMetadataPostwriteOps(Protocol):
    async def log_silver_audit(
        self,
        table_name: str,
        records: list[BronzeRecord],
        mode: str,
        validated_mode: SilverWriteMode,
        run_id: RunID | None = None,
        run_type: RunType | None = None,
        source_batch_id: BatchID | None = None,
        ingestion_ts: datetime | None = None,
        error: str | None = None,
    ) -> None: ...


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


class _SilverPostwriteHostProtocol(Protocol):
    """Structural type for postwrite service dependencies."""

    base_path: str | Path
    _maintenance: _SilverMaintenancePostwriteOps | None
    _metadata: _SilverMetadataPostwriteOps | None

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


class _SilverPostwriteFinalizerProtocol(Protocol):
    """Keyword-friendly finalization callable shared by mixin and service paths."""

    async def __call__(
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


class _SilverPostwriteExecutorProtocol(Protocol):
    """Shared postwrite executor contract for mixin and operations implementations."""

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
