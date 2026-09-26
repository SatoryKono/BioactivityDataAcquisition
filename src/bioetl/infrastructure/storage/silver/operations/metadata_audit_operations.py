"""Audit helper bindings for Silver metadata operations."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.ports import AuditPort
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.infrastructure.storage.silver.operations.metadata_write_support import (
    _log_silver_audit_event,
    _SilverMetadataAuditSupportRequest,
)


class _SilverMetadataAuditOps(Protocol):
    """Minimal facade surface needed by Silver metadata audit helpers."""

    @property
    def _audit(self) -> AuditPort | None: ...


async def log_silver_audit_via_support_request(
    metadata_ops: _SilverMetadataAuditOps,
    *,
    table_name: str,
    records: list[BronzeRecord],
    validated_mode: SilverWriteMode,
    run_id: RunID | None = None,
    run_type: RunType | None = None,
    source_batch_id: BatchID | None = None,
    ingestion_ts: datetime | None = None,
) -> None:
    """Log one Silver audit event when the audit port is configured."""
    if not metadata_ops._audit:
        return

    await _log_silver_audit_event(
        metadata_ops,
        _SilverMetadataAuditSupportRequest(
            table_name=table_name,
            records=records,
            mode=validated_mode,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
        ),
    )


async def log_silver_audit_operation(
    metadata_ops: _SilverMetadataAuditOps,
    *,
    table_name: str,
    records: list[BronzeRecord],
    mode: str,
    validated_mode: SilverWriteMode,
    run_id: RunID | None = None,
    run_type: RunType | None = None,
    source_batch_id: BatchID | None = None,
    ingestion_ts: datetime | None = None,
    error: str | None = None,
) -> None:
    """Log Silver write audit event."""
    del mode, error
    await log_silver_audit_via_support_request(
        metadata_ops,
        table_name=table_name,
        records=records,
        validated_mode=validated_mode,
        run_id=run_id,
        run_type=run_type,
        source_batch_id=source_batch_id,
        ingestion_ts=ingestion_ts,
    )


async def log_internal_silver_audit_operation(
    metadata_ops: _SilverMetadataAuditOps,
    request: _SilverMetadataAuditSupportRequest,
) -> None:
    """Log one Silver audit event from an internal request payload."""
    await _log_silver_audit_event(
        metadata_ops,
        request,
    )
