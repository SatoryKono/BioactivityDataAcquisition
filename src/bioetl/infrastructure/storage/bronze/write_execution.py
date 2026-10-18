"""Execution helpers for Bronze writer orchestration."""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Protocol

import orjson

from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.ports import AuditPort
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.storage.bronze.io_mixin import write_bytes_if_absent_or_same
from bioetl.infrastructure.storage.bronze.pipeline_helpers import (
    BronzeWriteArtifacts,
    BronzeWritePostwriteContext,
    BronzeWritePrepared,
    build_bronze_write_artifacts,
)


class _BronzeWriteExecutionHostProtocol(Protocol):
    """Host contract for Bronze write execution and post-write side effects."""

    save_json: bool
    _audit: AuditPort | None
    _save_metadata: bool

    def _write_atomic_stream(
        self,
        records: Iterator[bytes],
        output_path: Path,
    ) -> tuple[int, int]: ...

    async def _write_json_copy(
        self,
        records: list[bytes],
        provider: str,
        entity: str,
        date_str: str,
        batch_id: BatchID,
        *,
        locked_root: Path | None = None,
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
        ingestion_ts: datetime,
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
        ingestion_ts: datetime,
        duration: float,
        source_metadata: SourceMetadata | None,
        locked_root: Path | None = None,
    ) -> None: ...


async def run_bronze_post_write_actions(
    host: _BronzeWriteExecutionHostProtocol,
    context: BronzeWritePostwriteContext,
    *,
    locked_root: Path | None = None,
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
    if host.save_json and write_artifacts.json_copy_allowed:
        await host._write_json_copy(
            prepared.record_list,
            request.provider,
            request.entity,
            prepared.date_str,
            request.batch_id,
            locked_root=locked_root,
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
            locked_root=locked_root,
        )


async def write_bronze_data_and_sidecar(
    host: _BronzeWriteExecutionHostProtocol,
    prepared: BronzeWritePrepared,
) -> BronzeWriteArtifacts:
    """Write compressed JSONL data and metadata sidecar to disk."""

    def _write_task() -> tuple[int, int, bool]:
        count, size = host._write_atomic_stream(
            prepared.records_iter,
            prepared.full_path,
        )
        meta_bytes = _bronze_sidecar_bytes(prepared, save_json=host.save_json)
        write_bytes_if_absent_or_same(
            prepared.meta_path,
            meta_bytes,
            mismatch_message=(
                "Bronze metadata sidecar already exists with different payload: "
                f"{prepared.meta_path}"
            ),
        )
        association = orjson.loads(meta_bytes).get("cleanup_association")
        # Keep the original attestation: retries cannot add an unattested copy.
        copy_allowed = association is None or association["copy_sha256"] is not None
        return count, size, copy_allowed

    record_count, uncompressed_size, copy_allowed = await asyncio.to_thread(_write_task)
    return build_bronze_write_artifacts(
        full_path=prepared.full_path,
        record_count=record_count,
        uncompressed_size=uncompressed_size,
        json_copy_allowed=copy_allowed,
    )


def _bronze_sidecar_bytes(prepared: BronzeWritePrepared, *, save_json: bool) -> bytes:
    """Attest new content, preserving an existing batch's ownership on retry."""
    with prepared.full_path.open("rb") as payload:
        payload_digest = hashlib.file_digest(payload, "sha256").hexdigest()
    copy_digest = hashlib.sha256()
    for record in prepared.record_list:
        copy_digest.update(record)
    metadata = {
        **prepared.metadata,
        "cleanup_association": {
            "schema": 1,
            "payload_sha256": payload_digest,
            "copy_sha256": copy_digest.hexdigest() if save_json else None,
        },
    }
    new_bytes: bytes = orjson.dumps(metadata, option=orjson.OPT_SORT_KEYS)
    try:
        with prepared.meta_path.open("rb") as existing:
            raw: bytes = existing.read(1_048_577)
    except FileNotFoundError:
        return new_bytes
    legacy_bytes = orjson.dumps(prepared.metadata, option=orjson.OPT_SORT_KEYS)
    if raw == legacy_bytes:
        return raw  # Legacy sidecars never acquire cleanup ownership on retry.
    requested_copy_digest = copy_digest.hexdigest() if save_json else None
    if _same_existing_association(
        raw,
        prepared,
        payload_digest,
        requested_copy_digest,
    ):
        return raw
    return new_bytes


def _same_existing_association(
    raw: bytes,
    prepared: BronzeWritePrepared,
    payload_digest: str,
    requested_copy_digest: str | None,
) -> bool:
    try:
        existing = orjson.loads(raw)
    except orjson.JSONDecodeError:
        return False
    if not isinstance(existing, dict):
        return False
    association = existing.get("cleanup_association")
    if not isinstance(association, dict):
        return False
    copy_digest = association.get("copy_sha256")
    if copy_digest is not None and not (
        isinstance(copy_digest, str)
        and len(copy_digest) == 64
        and all(char in "0123456789abcdef" for char in copy_digest)
    ):
        return False
    if (
        requested_copy_digest is not None
        and copy_digest is not None
        and copy_digest != requested_copy_digest
    ):
        return False
    expected = {
        **prepared.metadata,
        "cleanup_association": {
            "schema": 1,
            "payload_sha256": payload_digest,
            "copy_sha256": copy_digest,
        },
    }
    # Exact canonical bytes reject ambiguous/foreign lineage, keys and schema.
    return raw == orjson.dumps(expected, option=orjson.OPT_SORT_KEYS)


__all__ = [
    "run_bronze_post_write_actions",
    "write_bronze_data_and_sidecar",
]
