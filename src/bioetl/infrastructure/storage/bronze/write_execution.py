"""Execution helpers for Bronze writer orchestration."""

from __future__ import annotations

import asyncio
from typing import Protocol

import orjson

from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.storage.bronze.pipeline_helpers import (
    BronzeWriteArtifacts,
    BronzeWritePostwriteContext,
    BronzeWritePrepared,
    build_bronze_write_artifacts,
)
from bioetl.infrastructure.storage.support.atomic_ops import atomic_write_bytes


class _BronzeWriteExecutionHostProtocol(Protocol):
    """Host contract for Bronze write execution and post-write side effects."""

    save_json: bool
    _audit: object | None
    _save_metadata: bool

    def _write_atomic_stream(
        self,
        records: object,
        output_path: object,
    ) -> tuple[int, int]: ...

    async def _write_json_copy(
        self,
        records: list[bytes],
        provider: str,
        entity: str,
        date_str: str,
        batch_id: BatchID,
    ) -> None: ...

    def _emit_bronze_write_metrics(
        self,
        *,
        duration: float,
        provider: str,
        entity: str,
        record_count: int,
        compressed_size: int,
        uncompressed_size: int,
        relative_path: str,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None: ...

    async def _log_bronze_audit(
        self,
        *,
        run_id: RunID,
        ingestion_ts: object,
        relative_path: str,
        batch_id: BatchID,
        run_type: RunType,
        record_count: int,
        compressed_size: int,
        uncompressed_size: int,
        provider: str,
        entity: str,
    ) -> None: ...

    async def _maybe_write_bronze_metadata(
        self,
        *,
        run_id: RunID,
        run_type: RunType,
        provider: str,
        entity: str,
        batch_id: BatchID,
        record_count: int,
        compressed_size: int,
        relative_path: str,
        ingestion_ts: object,
        duration: float,
        source_metadata: object | None,
    ) -> None: ...


async def run_bronze_post_write_actions(
    host: _BronzeWriteExecutionHostProtocol,
    context: BronzeWritePostwriteContext,
) -> None:
    """Emit metrics, optional JSON copy, audit log, and metadata sidecar."""
    request = context.request
    prepared = context.prepared
    write_artifacts = context.write_artifacts
    host._emit_bronze_write_metrics(
        duration=context.duration,
        provider=request.provider,
        entity=request.entity,
        record_count=write_artifacts.record_count,
        compressed_size=write_artifacts.compressed_size,
        uncompressed_size=write_artifacts.uncompressed_size,
        relative_path=prepared.relative_path,
        batch_id=request.batch_id,
        run_id=request.run_id,
        run_type=request.run_type,
    )
    if host.save_json:
        await host._write_json_copy(
            prepared.record_list,
            request.provider,
            request.entity,
            prepared.date_str,
            request.batch_id,
        )
    if host._audit:
        await host._log_bronze_audit(
            run_id=request.run_id,
            ingestion_ts=request.ingestion_ts,
            relative_path=prepared.relative_path,
            batch_id=request.batch_id,
            run_type=request.run_type,
            record_count=write_artifacts.record_count,
            compressed_size=write_artifacts.compressed_size,
            uncompressed_size=write_artifacts.uncompressed_size,
            provider=request.provider,
            entity=request.entity,
        )
    if host._save_metadata:
        await host._maybe_write_bronze_metadata(
            run_id=request.run_id,
            run_type=request.run_type,
            provider=request.provider,
            entity=request.entity,
            batch_id=request.batch_id,
            record_count=write_artifacts.record_count,
            compressed_size=write_artifacts.compressed_size,
            relative_path=prepared.relative_path,
            ingestion_ts=request.ingestion_ts,
            duration=context.duration,
            source_metadata=request.source_metadata,
        )


async def write_bronze_data_and_sidecar(
    host: _BronzeWriteExecutionHostProtocol,
    prepared: BronzeWritePrepared,
) -> BronzeWriteArtifacts:
    """Write compressed JSONL data and metadata sidecar to disk."""

    def _write_task() -> tuple[int, int]:
        count, size = host._write_atomic_stream(
            prepared.records_iter,
            prepared.full_path,
        )
        meta_bytes = orjson.dumps(prepared.metadata, option=orjson.OPT_SORT_KEYS)
        atomic_write_bytes(prepared.meta_path, meta_bytes)
        return count, size

    record_count, uncompressed_size = await asyncio.to_thread(_write_task)
    return build_bronze_write_artifacts(
        full_path=prepared.full_path,
        record_count=record_count,
        uncompressed_size=uncompressed_size,
    )


__all__ = [
    "run_bronze_post_write_actions",
    "write_bronze_data_and_sidecar",
]
